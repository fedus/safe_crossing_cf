from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import City, CityVersion, Crossing, Vote, db, AppConfig, NotificationLog, User
from functools import wraps
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import func, distinct

firebase_app = None
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    # Initialize Firebase Admin once if credentials available
    if not firebase_admin._apps:
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if cred_path and os.path.exists(cred_path):
            try:
                # Derive projectId from the service account file
                import json as _json
                with open(cred_path, 'r', encoding='utf-8') as f:
                    _cfg = _json.load(f)
                _project_id = _cfg.get('project_id') or os.getenv('GOOGLE_CLOUD_PROJECT')
                opts = {'projectId': _project_id} if _project_id else None
                firebase_app = firebase_admin.initialize_app(credentials.Certificate(cred_path), options=opts)
            except Exception:
                firebase_app = firebase_admin.initialize_app(credentials.Certificate(cred_path))
        else:
            # Allow running without credentials; sending will error gracefully
            pass
except Exception:
    # firebase-admin not installed or init failed; test/send endpoints will report error
    firebase_admin = None
    messaging = None

def ensure_fcm_initialized():
    global firebase_app, firebase_admin, credentials
    if messaging is None:
        return False
    try:
        if firebase_admin is None:
            return False
        if not firebase_admin._apps:
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if cred_path and os.path.exists(cred_path):
                try:
                    import json as _json
                    with open(cred_path, 'r', encoding='utf-8') as f:
                        _cfg = _json.load(f)
                    _project_id = _cfg.get('project_id') or os.getenv('GOOGLE_CLOUD_PROJECT')
                    opts = {'projectId': _project_id} if _project_id else None
                    firebase_app = firebase_admin.initialize_app(credentials.Certificate(cred_path), options=opts)
                except Exception:
                    firebase_app = firebase_admin.initialize_app(credentials.Certificate(cred_path))
            else:
                # Attempt default initialization (ADC) if no explicit cert
                firebase_app = firebase_admin.initialize_app()
        return True
    except Exception:
        return False
def _classify_fcm_error(exc: Exception) -> str:
    text = str(exc) or ''
    lower = text.lower()
    if 'not registered' in lower or 'registration-token-not-registered' in lower:
        return 'not_registered'
    if 'mismatchsenderid' in lower or 'mismatch sender' in lower:
        return 'mismatch_sender'
    if 'invalid argument' in lower or 'invalidargument' in lower or 'malformed' in lower:
        return 'invalid_token'
    if 'apns' in lower:
        return 'apns_auth'
    if 'web push' in lower or 'vapid' in lower:
        return 'webpush_auth'
    if 'project id is required' in lower:
        return 'missing_project_id'
    return 'unknown'

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be an admin to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def index():
    cities = City.query.all()
    config = AppConfig.get_solo()
    return render_template('admin/index.html', cities=cities, config=config)

@admin_bp.route('/notifications', methods=['GET', 'POST'])
@login_required
@admin_required
def notifications():
    # Ensure tables exist (for environments without migrations run)
    try:
        db.create_all()
    except Exception:
        pass
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        data_raw = request.form.get('data', '').strip()
        target_user_id = request.form.get('target_user_id', '').strip()  # optional for test send
        action = request.form.get('action', 'test').strip()  # 'test' | 'preview' | 'send'

        # Segment filters (optional)
        city_id = request.form.get('city_id', type=int)
        version_id = request.form.get('version_id', type=int)
        activity = request.form.get('activity', '').strip()  # never_voted | inactive | has_unvoted | completed
        inactive_days = request.form.get('inactive_days', type=int)
        require_fcm = True  # default: only users with tokens

        try:
            data_json = json.loads(data_raw) if data_raw else {}
        except Exception as e:
            flash(f'Invalid data JSON: {str(e)}', 'error')
            return redirect(url_for('admin.notifications'))

        log = NotificationLog(
            created_by=str(getattr(current_user, 'id', '')),
            title=title,
            body=body,
            data_json=json.dumps(data_json),
            target_user_id=target_user_id or None,
            status='logged'
        )
        db.session.add(log)
        db.session.commit()

        # If a specific target user ID is provided, perform an immediate test send
        if target_user_id:
            return _send_test_to_user(log.id, target_user_id)

        # Build segment
        users_q = _build_segment_query(city_id=city_id, version_id=version_id,
                                       activity=activity, inactive_days=inactive_days,
                                       require_fcm=require_fcm)

        if action == 'preview':
            try:
                total = users_q.count()
                sample = [u.id for u in users_q.limit(10).all()]
                flash(f'Preview: {total} users match. Sample: {", ".join(sample)}', 'info')
            except Exception as e:
                flash(f'Preview failed: {str(e)}', 'error')
            return redirect(url_for('admin.notifications'))

        if action == 'send':
            if not ensure_fcm_initialized():
                flash('FCM not configured on server', 'error')
                return redirect(url_for('admin.notifications'))
            sent = 0
            errors = 0
            error_samples = []
            error_buckets = {}
            users_to_null = []
            try:
                users = users_q.all()
                for u in users:
                    if not u.fcm_token:
                        continue
                    try:
                        data_payload = json.loads(log.data_json) if log.data_json else {}
                        message = messaging.Message(
                            token=u.fcm_token,
                            notification=messaging.Notification(title=log.title or '', body=log.body or ''),
                            data={k: str(v) for k, v in data_payload.items()}
                        )
                        resp = messaging.send(message, app=firebase_app)
                        sent += 1
                    except Exception as e:
                        errors += 1
                        if len(error_samples) < 5:
                            # Collect a few sample error messages for debugging
                            error_samples.append(str(e))
                        code = _classify_fcm_error(e)
                        error_buckets[code] = error_buckets.get(code, 0) + 1
                        if code == 'not_registered':
                            users_to_null.append(u.id)
                log.sent_count = sent
                log.error_count = errors
                log.status = 'sent' if errors == 0 else 'failed'
                db.session.commit()
                # Null out dead tokens
                if users_to_null:
                    try:
                        User.query.filter(User.id.in_(users_to_null)).update({User.fcm_token: None}, synchronize_session=False)
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                if errors == 0:
                    flash(f'Send complete: sent={sent}, errors={errors}', 'success')
                else:
                    detail = '; '.join(error_samples)
                    bucket_str = ', '.join([f"{k}:{v}" for k, v in error_buckets.items()]) if error_buckets else 'n/a'
                    flash(f'Send complete: sent={sent}, errors={errors}. Sample errors: {detail}. Types: {bucket_str}', 'warning')
            except Exception as e:
                flash(f'Send failed: {str(e)}', 'error')
            return redirect(url_for('admin.notifications'))

        flash('Notification logged. Choose Preview or Send.', 'success')
        return redirect(url_for('admin.notifications'))

    try:
        logs = NotificationLog.query.order_by(NotificationLog.created_at.desc()).limit(50).all()
    except Exception:
        logs = []
    return render_template('admin/notifications.html', notification_logs=logs)

def _build_segment_query(city_id=None, version_id=None, activity=None, inactive_days=None, require_fcm=True):
    q = db.session.query(User)
    if require_fcm:
        q = q.filter(User.fcm_token.isnot(None))

    # Activity filters
    if activity == 'never_voted':
        q = q.outerjoin(Vote, Vote.user_id == User.id).group_by(User.id).having(func.count(Vote.id) == 0)
    elif activity == 'inactive' and inactive_days is not None and inactive_days > 0:
        last_vote_sub = db.session.query(Vote.user_id.label('uid'), func.max(Vote.created_at).label('last_voted')).group_by(Vote.user_id).subquery()
        cutoff = datetime.utcnow() - timedelta(days=inactive_days)
        q = q.outerjoin(last_vote_sub, last_vote_sub.c.uid == User.id).filter(
            (last_vote_sub.c.last_voted.is_(None)) | (last_vote_sub.c.last_voted <= cutoff)
        )

    # City/version participation
    if city_id or version_id:
        # Join votes->crossing for scoping
        q = q.join(Vote, Vote.user_id == User.id, isouter=True).join(Crossing, Crossing.id == Vote.crossing_id, isouter=True)
        if city_id:
            q = q.filter((Crossing.city_id == city_id) | (Crossing.city_id.is_(None)))
        if version_id:
            q = q.filter((Crossing.version_id == version_id) | (Crossing.version_id.is_(None)))
        q = q.group_by(User.id)

        total_crossings_q = db.session.query(func.count(Crossing.id))
        if city_id:
            total_crossings_q = total_crossings_q.filter(Crossing.city_id == city_id)
        if version_id:
            total_crossings_q = total_crossings_q.filter(Crossing.version_id == version_id)
        total_crossings = total_crossings_q.scalar() or 0

        if activity == 'completed' and total_crossings > 0:
            voted_count = func.count(distinct(Vote.crossing_id))
            q = q.having(voted_count >= total_crossings)
        elif activity == 'has_unvoted' and total_crossings > 0:
            voted_count = func.count(distinct(Vote.crossing_id))
            q = q.having((voted_count.is_(None)) | (voted_count < total_crossings))

    return q

def _send_test_to_user(log_id, user_id):
    log = NotificationLog.query.get(log_id)
    if not log:
        flash('Notification log not found', 'error')
        return redirect(url_for('admin.notifications'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.notifications'))

    if not user.fcm_token:
        flash('User has no FCM token linked', 'error')
        return redirect(url_for('admin.notifications'))

    if messaging is None:
        flash('FCM not configured on server', 'error')
        return redirect(url_for('admin.notifications'))

    try:
        data_payload = json.loads(log.data_json) if log.data_json else {}
        message = messaging.Message(
            token=user.fcm_token,
            notification=messaging.Notification(title=log.title or '', body=log.body or ''),
            data={k: str(v) for k, v in data_payload.items()}
        )
        response = messaging.send(message, app=firebase_app)
        log.sent_count = (log.sent_count or 0) + 1
        log.status = 'sent'
        db.session.commit()
        flash(f'Test message sent. Message ID: {response}', 'success')
    except Exception as e:
        log.error_count = (log.error_count or 0) + 1
        log.status = 'failed'
        db.session.commit()
        flash(f'Failed to send test message: {str(e)}', 'error')
    return redirect(url_for('admin.notifications'))

@admin_bp.route('/settings', methods=['POST'])
@login_required
@admin_required
def update_settings():
    try:
        votes_limit = request.form.get('votes_limit', type=int)
        if votes_limit is None or votes_limit < 1:
            flash('Votes threshold must be a positive integer', 'error')
            return redirect(url_for('admin.index'))
        cfg = AppConfig.get_solo()
        cfg.votes_limit = votes_limit
        db.session.commit()
        flash('Settings updated', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to update settings: {str(e)}', 'error')
    return redirect(url_for('admin.index'))

@admin_bp.route('/cities', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_cities():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        information_text = request.form.get('information_text', '')
        icon_url = request.form.get('icon_url', '')
        subtitle = request.form.get('subtitle', '')
        
        if not name:
            flash('City name is required', 'error')
            return redirect(url_for('admin.manage_cities'))
            
        city = City(name=name, description=description, information_text=information_text, 
                    icon_url=icon_url, subtitle=subtitle)
        db.session.add(city)
        db.session.commit()
        flash('City added successfully', 'success')
        return redirect(url_for('admin.manage_cities'))
        
    cities = City.query.all()
    return render_template('admin/cities.html', cities=cities)

@admin_bp.route('/cities/<int:city_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_city(city_id):
    city = City.query.get_or_404(city_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        information_text = request.form.get('information_text', '')
        icon_url = request.form.get('icon_url', '')
        subtitle = request.form.get('subtitle', '')
        
        if not name:
            flash('City name is required', 'error')
            return redirect(url_for('admin.edit_city', city_id=city_id))
        
        city.name = name
        city.description = description
        city.information_text = information_text
        city.icon_url = icon_url
        city.subtitle = subtitle
        db.session.commit()
        
        flash('City updated successfully', 'success')
        return redirect(url_for('admin.manage_cities'))
    
    return render_template('admin/edit_city.html', city=city)

@admin_bp.route('/cities/<int:city_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_city(city_id):
    city = City.query.get_or_404(city_id)
    
    # Check if there are any crossings associated with this city
    if city.crossings:
        flash('Cannot delete city with existing crossings', 'error')
        return redirect(url_for('admin.manage_cities'))
    
    # Delete all versions first
    CityVersion.query.filter_by(city_id=city_id).delete()
    
    # Delete the city
    db.session.delete(city)
    db.session.commit()
    
    flash('City deleted successfully', 'success')
    return redirect(url_for('admin.manage_cities'))

@admin_bp.route('/cities/<int:city_id>/versions', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_versions(city_id):
    city = City.query.get_or_404(city_id)
    
    if request.method == 'POST':
        version_number = request.form.get('version_number')
        description = request.form.get('description')
        
        if not version_number:
            flash('Version number is required', 'error')
            return redirect(url_for('admin.manage_versions', city_id=city_id))
            
        version = CityVersion(
            city_id=city_id,
            version_number=version_number,
            description=description
        )
        db.session.add(version)
        db.session.commit()
        flash('Version added successfully', 'success')
        return redirect(url_for('admin.manage_versions', city_id=city_id))
        
    versions = CityVersion.query.filter_by(city_id=city_id).all()
    return render_template('admin/versions.html', city=city, versions=versions)

@admin_bp.route('/versions/<int:version_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_version(version_id):
    version = CityVersion.query.get_or_404(version_id)
    city_id = version.city_id
    
    # Check if there are any crossings associated with this version
    if version.crossings:
        flash('Cannot delete version with existing crossings', 'error')
        return redirect(url_for('admin.manage_versions', city_id=city_id))
    
    # Delete the version
    db.session.delete(version)
    db.session.commit()
    
    flash('Version deleted successfully', 'success')
    return redirect(url_for('admin.manage_versions', city_id=city_id))

@admin_bp.route('/versions/<int:version_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_version_active(version_id):
    version = CityVersion.query.get_or_404(version_id)
    
    # Deactivate all other versions of this city
    CityVersion.query.filter_by(city_id=version.city_id).update({'is_active': False})
    
    # Toggle the selected version
    version.is_active = not version.is_active
    db.session.commit()
    
    return jsonify({'success': True, 'is_active': version.is_active})

@admin_bp.route('/versions/<int:version_id>/toggle_completed', methods=['POST'])
@login_required
@admin_required
def toggle_version_completed(version_id):
    version = CityVersion.query.get_or_404(version_id)
    version.is_completed = not version.is_completed
    db.session.commit()
    
    return jsonify({'success': True, 'is_completed': version.is_completed})

@admin_bp.route('/cities/<int:city_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_city_active(city_id):
    city = City.query.get_or_404(city_id)
    city.is_active = not city.is_active
    db.session.commit()
    
    return jsonify({'success': True, 'is_active': city.is_active})

@admin_bp.route('/cities/<int:city_id>/versions/<int:version_id>/crossings', methods=['GET'])
@login_required
@admin_required
def manage_crossings(city_id, version_id):
    city = City.query.get_or_404(city_id)
    version = CityVersion.query.get_or_404(version_id)
    crossings = Crossing.query.filter_by(city_id=city_id, version_id=version_id).all()

    # Live aggregates per crossing
    from sqlalchemy import func, case
    counts_rows = db.session.query(
        Vote.crossing_id,
        func.sum(case((Vote.vote == 1, 1), else_=0)).label('okay'),
        func.sum(case((Vote.vote == -1, 1), else_=0)).label('not_okay'),
        func.sum(case((Vote.vote == 0, 1), else_=0)).label('dont_know'),
        func.count(Vote.id).label('total')
    ).filter(
        Vote.crossing_id.in_([c.id for c in crossings])
    ).group_by(Vote.crossing_id).all()

    counts_by_crossing = {row.crossing_id: {
        'okay': int(row.okay or 0),
        'not_okay': int(row.not_okay or 0),
        'dont_know': int(row.dont_know or 0),
        'total': int(row.total or 0)
    } for row in counts_rows}

    return render_template('admin/crossings.html', city=city, version=version, crossings=crossings, counts_by_crossing=counts_by_crossing)

@admin_bp.route('/crossings/bulk-import', methods=['POST'])
@login_required
@admin_required
def bulk_import_crossings():
    try:
        data = request.get_json()
        crossings_data = data.get('crossings', [])
        city_id = data.get('city_id')
        version_id = data.get('version_id')
        
        if not all([city_id, version_id]):
            return jsonify({'error': 'City ID and Version ID are required'}), 400
            
        # Verify city and version exist
        city = City.query.get(city_id)
        version = CityVersion.query.get(version_id)
        if not city or not version:
            return jsonify({'error': 'Invalid city or version'}), 400
            
        # Process each crossing
        for crossing_data in crossings_data:
            crossing = Crossing(
                id=crossing_data.get('nodeId'),
                city_id=city_id,
                version_id=version_id,
                lat=crossing_data.get('lat'),
                lon=crossing_data.get('lon'),
                neighbourhood=crossing_data.get('neighbourhood'),
                street=crossing_data.get('street')
            )
            db.session.add(crossing)
            
        db.session.commit()
        return jsonify({'message': f'Successfully imported {len(crossings_data)} crossings'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/crossings/<path:crossing_id>', methods=['PUT'])
@login_required
@admin_required
def update_crossing(crossing_id):
    try:
        crossing = Crossing.query.get_or_404(crossing_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'lat' in data:
            crossing.lat = data['lat']
        if 'lon' in data:
            crossing.lon = data['lon']
        if 'neighbourhood' in data:
            crossing.neighbourhood = data['neighbourhood']
        if 'street' in data:
            crossing.street = data['street']
            
        db.session.commit()
        return jsonify({'message': 'Crossing updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/crossings/<path:crossing_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_crossing(crossing_id):
    try:
        crossing = Crossing.query.get_or_404(crossing_id)
        db.session.delete(crossing)
        db.session.commit()
        return jsonify({'message': 'Crossing deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 