class TestingConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database for testing
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key'  # Change this in production

class DevelopmentConfig:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///safe_crossing.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key'  # Change this in production 