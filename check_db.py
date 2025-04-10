from app import create_app, db
from app.models.models import User

def check_db():
    app = create_app()
    with app.app_context():
        # Check if tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print("Existing tables:", tables)
        
        # Try to query the user table if it exists
        if 'user' in tables:
            users = User.query.all()
            print("\nUsers in database:")
            for user in users:
                print(f"ID: {user.id}, Admin: {user.is_admin}")

if __name__ == '__main__':
    check_db() 