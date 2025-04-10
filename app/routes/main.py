from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.models import Crossing, Meta, User, City, CityVersion, Vote
from datetime import datetime, timedelta

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    cities = City.query.filter_by(is_active=True).all()
    
    # Get count of votes in the last 24 hours
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_votes = Vote.query.filter(Vote.created_at >= last_24h).count()
    
    # Get statistics
    meta = Meta.query.first()
    stats = {
        'crossings_with_enough_votes': meta.crossings_with_enough_votes if meta else 0,
        'votes_not_sure': meta.votes_not_sure if meta else 0,
        'votes_ok': meta.votes_ok if meta else 0,
        'votes_too_close': meta.votes_too_close if meta else 0,
        'votes_tie': meta.votes_tie if meta else 0
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
        'lon': c.lon,
        'votes_not_sure': c.votes_not_sure,
        'votes_ok': c.votes_ok,
        'votes_too_close': c.votes_too_close,
        'votes_total': c.votes_total,
        'current_result': c.current_result
    } for c in crossings])

@bp.route('/stats')
def get_stats():
    meta = Meta.query.first()
    if not meta:
        return jsonify({
            'crossings_with_enough_votes': 0,
            'votes_not_sure': 0,
            'votes_ok': 0,
            'votes_too_close': 0,
            'votes_tie': 0
        })
    
    return jsonify({
        'crossings_with_enough_votes': meta.crossings_with_enough_votes,
        'votes_not_sure': meta.votes_not_sure,
        'votes_ok': meta.votes_ok,
        'votes_too_close': meta.votes_too_close,
        'votes_tie': meta.votes_tie
    }) 