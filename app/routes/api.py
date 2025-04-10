from flask import Blueprint, jsonify, request
from app import db
from app.models.models import User, Crossing, Vote, UnseenCrossing, Meta
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
    
    # Get all crossings
    crossings = Crossing.query.all()
    
    # Create user if not exists
    if not user:
        user = User(id=user_uuid)
        db.session.add(user)
    
    # Mark all crossings as unseen by this user
    for crossing in crossings:
        unseen = UnseenCrossing(user_id=user_uuid, crossing_id=crossing.id)
        db.session.add(unseen)
    
    user.initialized = True
    db.session.commit()
    
    return jsonify({'status': 'USER_INITIALIZED'})

@bp.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()
    user_uuid = data.get('userUuid')
    crossing_node_id = data.get('crossingNodeId')
    vote_value = data.get('vote')
    
    if not all([user_uuid, crossing_node_id, vote_value is not None]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Get or create meta record
    meta = Meta.query.first()
    if not meta:
        meta = Meta()
        db.session.add(meta)
    
    # Get crossing
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
        
        # Remove from unseen
        UnseenCrossing.query.filter_by(
            user_id=user_uuid,
            crossing_id=crossing_node_id
        ).delete()
    
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