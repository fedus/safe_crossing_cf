from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name=None):
    app = Flask(__name__)
    CORS(app)
    
    if config_name == 'testing':
        app.config.from_object('config.TestingConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    # Register blueprints
    from app.routes import main, api, admin
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(admin.admin_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app 