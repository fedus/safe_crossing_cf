from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import City, CityVersion, Crossing, Vote, db
from functools import wraps
import json

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
    return render_template('admin/index.html', cities=cities)

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