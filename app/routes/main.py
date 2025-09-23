from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.models import Crossing, User, City, CityVersion, Vote
from datetime import datetime, timedelta

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    cities = City.query.filter_by(is_active=True).all()
    
    # Get count of votes in the last 24 hours
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_votes = Vote.query.filter(Vote.created_at >= last_24h).count()
    
    # Live statistics from Vote rows
    from sqlalchemy import func, case
    # Count crossings with enough votes across active versions
    active_version_ids = []
    for city in cities:
        av = CityVersion.query.filter_by(city_id=city.id, is_active=True).first()
        if av:
            active_version_ids.append(av.id)

    votes_limit = 5

    # Crossings with enough votes
    crossings_with_enough_votes = 0
    if active_version_ids:
        votes_per_crossing_subq = db.session.query(
            Crossing.id.label('crossing_id'),
            func.count(Vote.id).label('vote_count')
        ).join(Vote, Vote.crossing_id == Crossing.id).filter(
            Crossing.version_id.in_(active_version_ids)
        ).group_by(Crossing.id).subquery()

        crossings_with_enough_votes = db.session.query(func.count()).filter(
            votes_per_crossing_subq.c.vote_count >= votes_limit
        ).scalar() or 0

    # Global distribution of vote categories
    vote_totals = db.session.query(
        func.sum(case((Vote.vote == 1, 1), else_=0)).label('votes_ok'),
        func.sum(case((Vote.vote == -1, 1), else_=0)).label('votes_too_close'),
        func.sum(case((Vote.vote == 0, 1), else_=0)).label('votes_not_sure')
    ).first()

    stats = {
        'crossings_with_enough_votes': int(crossings_with_enough_votes),
        'votes_not_sure': int((vote_totals.votes_not_sure or 0)),
        'votes_ok': int((vote_totals.votes_ok or 0)),
        'votes_too_close': int((vote_totals.votes_too_close or 0)),
        'votes_tie': 0
    }
    
    # Get total active crossings
    active_versions = {}
    for city in cities:
        active_version = CityVersion.query.filter_by(
            city_id=city.id,
            is_active=True
        ).first()
        if active_version:
            active_versions[city.id] = active_version.id

    total_crossings = Crossing.query.filter(
        Crossing.city_id.in_(active_versions.keys()),
        Crossing.version_id.in_(active_versions.values())
    ).count()
    
    # Total votes
    total_votes = Vote.query.count()
    
    return render_template('index.html', 
                           cities=cities, 
                           recent_votes=recent_votes,
                           stats=stats,
                           total_crossings=total_crossings,
                           total_votes=total_votes)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        user = User.query.get(user_id)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin.index'))
        else:
            flash('Invalid user ID or password', 'error')
    
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/crossings')
def get_crossings():
    # Get active version for each active city
    active_versions = {}
    for city in City.query.filter_by(is_active=True).all():
        active_version = CityVersion.query.filter_by(
            city_id=city.id,
            is_active=True
        ).first()
        if active_version:
            active_versions[city.id] = active_version.id

    # Get crossings for active versions
    crossings = Crossing.query.filter(
        Crossing.city_id.in_(active_versions.keys()),
        Crossing.version_id.in_(active_versions.values())
    ).all()

    return jsonify([{
        'id': c.id,
        'city_id': c.city_id,
        'city_name': c.city.name,
        'version_id': c.version_id,
        'version': c.version.version_number,
        'lat': c.lat,
        'lon': c.lon
    } for c in crossings])

@bp.route('/stats')
def get_stats():
    from sqlalchemy import func, case
    votes_limit = 5

    # Crossings with enough votes across all active versions
    active_versions = CityVersion.query.filter_by(is_active=True).all()
    active_version_ids = [v.id for v in active_versions]

    crossings_with_enough_votes = 0
    if active_version_ids:
        votes_per_crossing_subq = db.session.query(
            Crossing.id.label('crossing_id'),
            func.count(Vote.id).label('vote_count')
        ).join(Vote, Vote.crossing_id == Crossing.id).filter(
            Crossing.version_id.in_(active_version_ids)
        ).group_by(Crossing.id).subquery()

        crossings_with_enough_votes = db.session.query(func.count()).filter(
            votes_per_crossing_subq.c.vote_count >= votes_limit
        ).scalar() or 0

    # Global distribution of vote categories
    totals = db.session.query(
        func.sum(case((Vote.vote == 1, 1), else_=0)).label('votes_ok'),
        func.sum(case((Vote.vote == -1, 1), else_=0)).label('votes_too_close'),
        func.sum(case((Vote.vote == 0, 1), else_=0)).label('votes_not_sure')
    ).first()

    return jsonify({
        'crossings_with_enough_votes': int(crossings_with_enough_votes),
        'votes_not_sure': int((totals.votes_not_sure or 0)),
        'votes_ok': int((totals.votes_ok or 0)),
        'votes_too_close': int((totals.votes_too_close or 0)),
        'votes_tie': 0
    })

@bp.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200 