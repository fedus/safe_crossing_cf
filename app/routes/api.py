from flask import Blueprint, jsonify, request
from app import db
from app.models.models import User, Crossing, Vote, City, CityVersion, UserDeviceToken
from sqlalchemy import func
import uuid
import random

bp = Blueprint('api', __name__)

@bp.route('/initialize-user', methods=['POST'])
def initialize_user():
    data = request.get_json()
    user_uuid = data.get('userUuid')
    
    if not user_uuid:
        return jsonify({'error': 'userUuid is required'}), 400
    
    # Check if user exists and is initialized
    user = User.query.get(user_uuid)
    if user and user.initialized:
        return jsonify({'status': 'USER_ALREADY_INITIALIZED'})
    
    # Create user if not exists
    if not user:
        user = User(id=user_uuid)
        db.session.add(user)
    
    user.initialized = True
    db.session.commit()
    
    return jsonify({'status': 'USER_INITIALIZED'})

@bp.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()
    user_uuid = data.get('userUuid')
    crossing_node_id = data.get('crossingNodeId')
    vote_value = data.get('vote')
    city_id = data.get('city_id')
    version_id = data.get('version_id')
    
    # Explicit validation to allow vote_value == 0
    if user_uuid is None or crossing_node_id is None or vote_value is None:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Validate vote value mapping: -1 = not_okay, 0 = dont_know, 1 = okay
    # Also accept legacy value 2 for backward compatibility (maps to -1)
    if vote_value not in (-1, 0, 1, 2):
        return jsonify({'error': 'Invalid vote value'}), 400
    
    # Map legacy value 2 to -1 for backward compatibility
    if vote_value == 2:
        vote_value = -1
    
    # Resolve crossing strictly by id; optionally check city/version if provided
    crossing_query = Crossing.query.filter_by(id=crossing_node_id)
    if city_id is not None:
        crossing_query = crossing_query.filter_by(city_id=city_id)
    if version_id is not None:
        crossing_query = crossing_query.filter_by(version_id=version_id)
    crossing = crossing_query.first()
    
    if not crossing:
        return jsonify({'error': 'Crossing not found'}), 404
    
    # Ensure user exists
    user = User.query.get(user_uuid)
    if not user:
        user = User(id=user_uuid, initialized=True)
        db.session.add(user)
    
    # Always insert a new vote (no upsert)
    new_vote = Vote(
        user_id=user_uuid,
        crossing_id=crossing_node_id,
        vote=vote_value
    )
    db.session.add(new_vote)
    db.session.commit()
    
    # Live aggregation of counts for this crossing
    from sqlalchemy import case
    counts = db.session.query(
        func.sum(case((Vote.vote == -1, 1), else_=0)).label('not_okay'),
        func.sum(case((Vote.vote == 0, 1), else_=0)).label('dont_know'),
        func.sum(case((Vote.vote == 1, 1), else_=0)).label('okay'),
        func.count(Vote.id).label('total')
    ).filter(
        Vote.crossing_id == crossing_node_id
    ).first()
    
    # Determine result in legacy scale: 0=cant_say, 1=ok, 2=too_close, 3=tie
    count_not_okay = counts.not_okay or 0
    count_dont_know = counts.dont_know or 0
    count_okay = counts.okay or 0
    max_count = max(count_not_okay, count_dont_know, count_okay)
    winners = [k for k, v in {
        'dont_know': count_dont_know,
        'okay': count_okay,
        'not_okay': count_not_okay
    }.items() if v == max_count]
    
    if len(winners) > 1:
        new_result = 3
    else:
        winner = winners[0]
        if winner == 'dont_know':
            new_result = 0
        elif winner == 'okay':
            new_result = 1
        else:
            new_result = 2
    
    return jsonify({
        'status': 'VOTE_RECORDED',
        'new_result': new_result,
        'counts': {
            'not_okay': count_not_okay,
            'dont_know': count_dont_know,
            'okay': count_okay,
            'total': counts.total or 0
        }
    })

def vote_enum_to_string(vote):
    # Updated mapping for readability in potential responses
    if vote == -1:
        return 'not_okay'
    elif vote == 0:
        return 'dont_know'
    elif vote == 1:
        return 'okay'
    else:
        return 'unknown'

@bp.route('/crossings', methods=['GET'])
def get_crossings():
    crossings = Crossing.query.all()
    return jsonify([{
        'id': c.id,
        'city_id': c.city_id,
        'version_id': c.version_id,
        'lat': c.lat,
        'lon': c.lon,
        'neighbourhood': c.neighbourhood,
        'street': c.street
    } for c in crossings])

@bp.route('/crossings/<crossing_id>', methods=['GET'])
def get_crossing(crossing_id):
    crossing = Crossing.query.get(crossing_id)
    if not crossing:
        return jsonify({'error': 'Crossing not found'}), 404
    return jsonify({
        'id': crossing.id,
        'city_id': crossing.city_id,
        'version_id': crossing.version_id,
        'lat': crossing.lat,
        'lon': crossing.lon,
        'neighbourhood': crossing.neighbourhood,
        'street': crossing.street
    })

@bp.route('/votes/<user_uuid>', methods=['GET'])
def get_user_votes(user_uuid):
    votes = Vote.query.filter_by(user_id=user_uuid).all()
    return jsonify([{
        'crossing_id': v.crossing_id,
        'vote': v.vote,
        'created_at': v.created_at.isoformat()
    } for v in votes])

@bp.route('/cities', methods=['GET'])
def get_cities():
    # Get all active cities
    cities = City.query.filter_by(is_active=True).all()
    result = []
    
    # Get active versions for all cities in one query
    active_versions = CityVersion.query.filter(
        CityVersion.city_id.in_([city.id for city in cities]),
        CityVersion.is_active == True
    ).all()
    
    # Create a mapping of city_id to active_version for quick lookup
    city_to_version = {version.city_id: version for version in active_versions}
    
    # For cities with active versions, get crossing statistics
    city_ids_with_versions = [v.city_id for v in active_versions]
    version_ids = [v.id for v in active_versions]
    
    # Import SQLAlchemy functions
    from sqlalchemy import func
    
    # Get count of crossings per city/version
    crossing_counts = db.session.query(
        Crossing.city_id,
        func.count(Crossing.id).label('total_crossings')
    ).filter(
        Crossing.city_id.in_(city_ids_with_versions),
        Crossing.version_id.in_(version_ids)
    ).group_by(Crossing.city_id).all()
    
    # Create mapping of city_id to crossing count
    city_to_crossing_count = {city_id: count for city_id, count in crossing_counts}
    
    # Get sum of votes per city/version using live Vote rows
    from sqlalchemy.orm import aliased
    Cv = aliased(Crossing)
    vote_counts = db.session.query(
        Cv.city_id,
        func.count(Vote.id).label('total_votes')
    ).join(Vote, Vote.crossing_id == Cv.id)
    vote_counts = vote_counts.filter(
        Cv.city_id.in_(city_ids_with_versions),
        Cv.version_id.in_(version_ids)
    ).group_by(Cv.city_id).all()
    
    # Create mapping of city_id to vote count
    city_to_vote_count = {city_id: count for city_id, count in vote_counts}
    
    # Get count of crossings with enough votes per city/version using Vote aggregates
    votes_limit = 5
    # Subquery: count votes per crossing
    votes_per_crossing_subq = db.session.query(
        Crossing.id.label('crossing_id'),
        Crossing.city_id.label('city_id'),
        func.count(Vote.id).label('vote_count')
    ).join(Vote, Vote.crossing_id == Crossing.id).filter(
        Crossing.city_id.in_(city_ids_with_versions),
        Crossing.version_id.in_(version_ids)
    ).group_by(Crossing.id).subquery()

    enough_votes_counts = db.session.query(
        votes_per_crossing_subq.c.city_id,
        func.count().label('crossings_with_enough_votes')
    ).filter(
        votes_per_crossing_subq.c.vote_count >= votes_limit
    ).group_by(votes_per_crossing_subq.c.city_id).all()
    
    # Create mapping of city_id to enough votes count
    city_to_enough_votes = {city_id: count for city_id, count in enough_votes_counts}
    
    # Build the result
    for city in cities:
        active_version = city_to_version.get(city.id)
        current_version = str(active_version.id) if active_version else ""
        
        # Get completion data from mappings
        total_crossings = city_to_crossing_count.get(city.id, 0)
        total_votes = city_to_vote_count.get(city.id, 0) or 0  # Handle None values
        crossings_with_enough_votes = city_to_enough_votes.get(city.id, 0)
        
        # Calculate completion percentage
        completion_percentage = 0
        if total_crossings > 0:
            completion_percentage = (crossings_with_enough_votes / total_crossings) * 100
        
        result.append({
            'id': city.id,
            'name': city.name,
            'informationText': city.information_text or "",
            'currentVersion': current_version,
            'icon_url': city.icon_url or "",
            'subtitle': city.subtitle or "",
            'completion': {
                'total_votes': total_votes,
                'votes_limit': votes_limit,
                'total_crossings': total_crossings,
                'crossings_with_enough_votes': crossings_with_enough_votes,
                'completion_percentage': round(completion_percentage, 2)
            }
        })
    
    return jsonify(result)

@bp.route('/cities/active', methods=['GET'])
def get_active_cities():
    """Returns a list of active cities in a simpler format as documented in the README."""
    cities = City.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': city.id,
        'name': city.name,
        'is_active': city.is_active
    } for city in cities])

@bp.route('/versions/active', methods=['GET'])
def get_active_versions():
    """Returns a list of active versions as documented in the README."""
    versions = CityVersion.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': version.id,
        'name': f"Version {version.version_number}",
        'is_active': version.is_active
    } for version in versions])

@bp.route('/cities/<int:city_id>/versions/<int:version_id>/crossings', methods=['GET'])
def get_city_version_crossings(city_id, version_id):
    crossings = Crossing.query.filter_by(
        city_id=city_id,
        version_id=version_id
    ).all()
    
    return jsonify([{
        'id': c.id,
        'lat': c.lat,
        'lon': c.lon,
        'neighbourhood': c.neighbourhood,
        'street': c.street
    } for c in crossings])

@bp.route('/cities/<int:city_id>/versions/<int:version_id>/unvoted', methods=['GET'])
def get_unvoted_crossings(city_id, version_id):
    user_uuid = request.args.get('userUuid')
    if not user_uuid:
        return jsonify({'error': 'userUuid is required'}), 400
    
    # Get all crossings for this city/version
    all_crossings = Crossing.query.filter_by(
        city_id=city_id,
        version_id=version_id
    ).all()
    
    # Get user's voted crossing ids once
    voted_crossing_ids = set(
        v.crossing_id for v in Vote.query.with_entities(Vote.crossing_id).filter_by(user_id=user_uuid).all()
    )

    # Filter out voted crossings
    unvoted_crossings = [c for c in all_crossings if c.id not in voted_crossing_ids]

    # Randomize the order of unvoted crossings
    random.shuffle(unvoted_crossings)

    return jsonify([{
        'id': c.id,
        'lat': c.lat,
        'lon': c.lon,
        'neighbourhood': c.neighbourhood,
        'street': c.street
    } for c in unvoted_crossings])

@bp.route('/users/link-fcm-token', methods=['POST'])
def link_fcm_token():
    data = request.get_json()
    user_id = data.get('user_id')
    fcm_token = data.get('fcm_token')
    platform = (data.get('platform') or '').lower()  # optional: ios|android|web
    
    if not all([user_id, fcm_token]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    user = User.query.get(user_id)
    if not user:
        # Auto-create user if needed
        user = User(id=user_id, initialized=True)
        db.session.add(user)
        db.session.flush()
    
    # Keep legacy single-token field for backward compatibility
    user.fcm_token = fcm_token
    
    # Upsert device token
    existing = UserDeviceToken.query.filter_by(token=fcm_token).first()
    if existing:
        existing.user_id = user.id
        existing.platform = platform or existing.platform
        existing.valid = True
    else:
        db.session.add(UserDeviceToken(user_id=user.id, token=fcm_token, platform=platform or None, valid=True))
    db.session.commit()
    
    return jsonify({'status': 'FCM_TOKEN_LINKED'})

@bp.route('/cities/<int:city_id>/completion', methods=['GET'])
def get_city_completion(city_id):
    """Get detailed completion statistics for a specific city."""
    from sqlalchemy import func
    
    # Find the active version for this city
    active_version = CityVersion.query.filter_by(city_id=city_id, is_active=True).first()
    
    if not active_version:
        return jsonify({'error': 'No active version found for this city'}), 404
    
    # Get total crossings count
    total_crossings = Crossing.query.filter_by(
        city_id=city_id,
        version_id=active_version.id
    ).count()
    
    # Get total votes sum and count of crossings with enough votes using live Vote rows
    votes_limit = 5

    # Total votes for this city/version
    total_votes = db.session.query(func.count(Vote.id)).join(
        Crossing, Vote.crossing_id == Crossing.id
    ).filter(
        Crossing.city_id == city_id,
        Crossing.version_id == active_version.id
    ).scalar() or 0

    # Count of crossings with enough votes (>= votes_limit)
    votes_per_crossing_subq = db.session.query(
        Crossing.id.label('crossing_id'),
        func.count(Vote.id).label('vote_count')
    ).join(Vote, Vote.crossing_id == Crossing.id).filter(
        Crossing.city_id == city_id,
        Crossing.version_id == active_version.id
    ).group_by(Crossing.id).subquery()

    crossings_with_enough_votes = db.session.query(func.count()).filter(
        votes_per_crossing_subq.c.vote_count >= votes_limit
    ).scalar() or 0
    
    # Calculate completion percentage
    completion_percentage = 0
    if total_crossings > 0:
        completion_percentage = (crossings_with_enough_votes / total_crossings) * 100
    
    return jsonify({
        'city_id': city_id,
        'version_id': active_version.id,
        'total_crossings': total_crossings,
        'total_votes': total_votes,
        'votes_limit': votes_limit,
        'crossings_with_enough_votes': crossings_with_enough_votes,
        'completion_percentage': round(completion_percentage, 2)
    }) 