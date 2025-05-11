from flask import Blueprint, jsonify, request
from app import db
from app.models.models import User, Crossing, Vote, Meta, City, CityVersion
from sqlalchemy import func
import uuid

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
    
    if not all([user_uuid, crossing_node_id, vote_value is not None]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Get or create meta record
    meta = Meta.query.first()
    if not meta:
        meta = Meta()
        db.session.add(meta)
    
    # Get crossing
    if city_id and version_id:
        # If city_id and version_id are provided, use them for a more specific query
        crossing = Crossing.query.filter_by(
            id=crossing_node_id,
            city_id=city_id,
            version_id=version_id
        ).first()
    else:
        # Fallback to original behavior for backward compatibility
        crossing = Crossing.query.get(crossing_node_id)
    
    if not crossing:
        return jsonify({'error': 'Crossing not found'}), 404
    
    # Get existing vote if any
    existing_vote = Vote.query.filter_by(
        user_id=user_uuid,
        crossing_id=crossing_node_id
    ).first()
    
    # Calculate new result
    votes = {
        'not_sure': crossing.votes_not_sure,
        'ok': crossing.votes_ok,
        'too_close': crossing.votes_too_close
    }
    
    if existing_vote:
        # Remove old vote
        votes[vote_enum_to_string(existing_vote.vote)] -= 1
    else:
        # New vote
        crossing.votes_total += 1
        user = User.query.get(user_uuid)
        user.total_votes_cast += 1
    
    # Add new vote
    votes[vote_enum_to_string(vote_value)] += 1
    
    # Update crossing votes
    crossing.votes_not_sure = votes['not_sure']
    crossing.votes_ok = votes['ok']
    crossing.votes_too_close = votes['too_close']
    
    # Calculate new result
    max_votes = max(votes.values())
    if votes['not_sure'] == max_votes:
        new_result = 0
    elif votes['ok'] == max_votes:
        new_result = 1
    elif votes['too_close'] == max_votes:
        new_result = 2
    else:
        new_result = 3
    
    # Update meta if crossing just reached 5 votes
    if crossing.votes_total == 5:
        meta.crossings_with_enough_votes += 1
        setattr(meta, f'votes_{vote_enum_to_string(new_result)}', 
                getattr(meta, f'votes_{vote_enum_to_string(new_result)}') + 1)
    elif crossing.votes_total > 5 and new_result != crossing.current_result:
        # Update meta for changed results
        setattr(meta, f'votes_{vote_enum_to_string(crossing.current_result)}',
                getattr(meta, f'votes_{vote_enum_to_string(crossing.current_result)}') - 1)
        setattr(meta, f'votes_{vote_enum_to_string(new_result)}',
                getattr(meta, f'votes_{vote_enum_to_string(new_result)}') + 1)
    
    crossing.current_result = new_result
    
    # Create or update vote
    if existing_vote:
        existing_vote.vote = vote_value
    else:
        new_vote = Vote(
            user_id=user_uuid,
            crossing_id=crossing_node_id,
            vote=vote_value
        )
        db.session.add(new_vote)
    
    db.session.commit()
    
    return jsonify({
        'status': 'VOTE_RECORDED',
        'new_result': new_result
    })

def vote_enum_to_string(vote):
    if vote == 0:
        return 'not_sure'
    elif vote == 1:
        return 'ok'
    elif vote == 2:
        return 'too_close'
    else:
        return 'tie'

@bp.route('/crossings', methods=['GET'])
def get_crossings():
    crossings = Crossing.query.all()
    return jsonify([{
        'id': c.id,
        'city': c.city,
        'version': c.version,
        'votes_not_sure': c.votes_not_sure,
        'votes_ok': c.votes_ok,
        'votes_too_close': c.votes_too_close,
        'votes_total': c.votes_total,
        'current_result': c.current_result
    } for c in crossings])

@bp.route('/crossings/<crossing_id>', methods=['GET'])
def get_crossing(crossing_id):
    crossing = Crossing.query.get(crossing_id)
    if not crossing:
        return jsonify({'error': 'Crossing not found'}), 404
    return jsonify({
        'id': crossing.id,
        'city': crossing.city,
        'version': crossing.version,
        'votes_not_sure': crossing.votes_not_sure,
        'votes_ok': crossing.votes_ok,
        'votes_too_close': crossing.votes_too_close,
        'votes_total': crossing.votes_total,
        'current_result': crossing.current_result
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
    
    # Get sum of votes per city/version
    vote_counts = db.session.query(
        Crossing.city_id,
        func.sum(Crossing.votes_total).label('total_votes')
    ).filter(
        Crossing.city_id.in_(city_ids_with_versions),
        Crossing.version_id.in_(version_ids)
    ).group_by(Crossing.city_id).all()
    
    # Create mapping of city_id to vote count
    city_to_vote_count = {city_id: count for city_id, count in vote_counts}
    
    # Get count of crossings with enough votes per city/version
    votes_limit = 5
    enough_votes_counts = db.session.query(
        Crossing.city_id,
        func.count(Crossing.id).label('crossings_with_enough_votes')
    ).filter(
        Crossing.city_id.in_(city_ids_with_versions),
        Crossing.version_id.in_(version_ids),
        Crossing.votes_total >= votes_limit
    ).group_by(Crossing.city_id).all()
    
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
        'street': c.street,
        'votes_not_sure': c.votes_not_sure,
        'votes_ok': c.votes_ok,
        'votes_too_close': c.votes_too_close,
        'votes_total': c.votes_total,
        'current_result': c.current_result
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
    
    # Get user's votes for these crossings
    voted_crossing_ids = set(
        v.crossing_id for v in Vote.query.filter_by(user_id=user_uuid).all()
    )
    
    # Filter out voted crossings
    unvoted_crossings = [
        c for c in all_crossings if c.id not in voted_crossing_ids
    ]
    
    return jsonify([{
        'id': c.id,
        'lat': c.lat,
        'lon': c.lon,
        'neighbourhood': c.neighbourhood,
        'street': c.street,
        'votes_not_sure': c.votes_not_sure,
        'votes_ok': c.votes_ok,
        'votes_too_close': c.votes_too_close,
        'votes_total': c.votes_total,
        'current_result': c.current_result
    } for c in unvoted_crossings])

@bp.route('/users/link-fcm-token', methods=['POST'])
def link_fcm_token():
    data = request.get_json()
    user_id = data.get('user_id')
    fcm_token = data.get('fcm_token')
    
    if not all([user_id, fcm_token]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.fcm_token = fcm_token
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
    
    # Get total votes sum and count of crossings with enough votes
    votes_limit = 5
    
    # Using a query to get total votes and crossings with enough votes
    result = db.session.query(
        func.sum(Crossing.votes_total).label('total_votes'),
        func.count(Crossing.id).filter(Crossing.votes_total >= votes_limit).label('crossings_with_enough_votes')
    ).filter(
        Crossing.city_id == city_id,
        Crossing.version_id == active_version.id
    ).first()
    
    if not result:
        return jsonify({
            'city_id': city_id,
            'version_id': active_version.id,
            'total_crossings': 0,
            'total_votes': 0,
            'votes_limit': votes_limit,
            'crossings_with_enough_votes': 0,
            'completion_percentage': 0
        })
    
    total_votes = result.total_votes or 0  # Handle None value
    crossings_with_enough_votes = result.crossings_with_enough_votes or 0  # Handle None value
    
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