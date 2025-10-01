from app import db, login_manager
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    votes_limit = db.Column(db.Integer, default=5)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_solo():
        try:
            cfg = AppConfig.query.get(1)
        except Exception:
            # Table may not exist yet; create missing tables and retry
            db.create_all()
            cfg = AppConfig.query.get(1)
        if not cfg:
            cfg = AppConfig(id=1, votes_limit=5)
            db.session.add(cfg)
            db.session.commit()
        return cfg

class User(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True)  # UUID
    initialized = db.Column(db.Boolean, default=False)
    total_votes_cast = db.Column(db.Integer, default=0)
    is_admin = db.Column(db.Boolean, default=False)  # New field for admin status
    password_hash = db.Column(db.String(128))
    fcm_token = db.Column(db.String(255), nullable=True)  # New field for FCM token
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class NotificationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(36))  # admin user id (uuid)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    data_json = db.Column(db.Text)
    target_user_id = db.Column(db.String(36), nullable=True)  # for test sends
    sent_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default='logged')  # logged|sent|failed

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    information_text = db.Column(db.Text)  # New field for HTML content
    icon_url = db.Column(db.String(255))  # URL for city icon
    subtitle = db.Column(db.String(255))  # Short tagline for the city
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    versions = db.relationship('CityVersion', backref='city', lazy=True)

class CityVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('city_id', 'version_number'),)

class Crossing(db.Model):
    id = db.Column(db.String(36), primary_key=True)  # OSM node ID
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    version_id = db.Column(db.Integer, db.ForeignKey('city_version.id'), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    neighbourhood = db.Column(db.String(100), nullable=True)
    street = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    city = db.relationship('City', backref='crossings')
    version = db.relationship('CityVersion', backref='crossings')
    votes = db.relationship('Vote', backref='crossing', lazy=True)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    crossing_id = db.Column(db.String(36), db.ForeignKey('crossing.id'), nullable=False)
    vote = db.Column(db.Integer, nullable=False)  # -1: NOT_OKAY, 0: DONT_KNOW, 1: OKAY
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Allow multiple votes from the same user for the same crossing; no uniqueness constraint

    