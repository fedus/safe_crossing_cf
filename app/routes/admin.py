from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.models import City, CityVersion, db
from functools import wraps

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
        
        if not name:
            flash('City name is required', 'error')
            return redirect(url_for('admin.manage_cities'))
            
        city = City(name=name, description=description)
        db.session.add(city)
        db.session.commit()
        flash('City added successfully', 'success')
        return redirect(url_for('admin.manage_cities'))
        
    cities = City.query.all()
    return render_template('admin/cities.html', cities=cities)

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