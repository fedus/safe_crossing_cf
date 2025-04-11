import os
import sys
import getpass
from app import create_app, db
from app.models.models import User, City, CityVersion, Crossing, Meta
from pathlib import Path

def init_db(admin_password=None):
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin = User.query.get('admin')
        if not admin:
            # Get password from environment variable, argument, or prompt
            if not admin_password:
                admin_password = os.getenv('ADMIN_PASSWORD')
            
            if not admin_password:
                while True:
                    admin_password = getpass.getpass("Enter password for admin user: ")
                    confirm = getpass.getpass("Confirm password: ")
                    if admin_password == confirm:
                        break
                    print("Passwords do not match. Please try again.")
            
            admin = User(
                id='admin',
                is_admin=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            print("Admin user created")
        else:
            print("Admin user already exists")
        
        # Create a sample city and version
        city = City(
            name='Sample City',
            description='A sample city for testing'
        )
        db.session.add(city)
        db.session.flush()  # Get the city ID
        
        version = CityVersion(
            city_id=city.id,
            version_number=1,
            description='Initial version',
            is_active=True
        )
        db.session.add(version)
        db.session.flush()  # Get the version ID
        
        # Create sample crossings
        sample_crossings = [
            {
                'id': 'node1',
                'lat': 49.6116,
                'lon': 6.1319,
                'city_id': city.id,
                'version_id': version.id
            },
            {
                'id': 'node2',
                'lat': 49.6117,
                'lon': 6.1320,
                'city_id': city.id,
                'version_id': version.id
            },
            {
                'id': 'node3',
                'lat': 49.6118,
                'lon': 6.1321,
                'city_id': city.id,
                'version_id': version.id
            }
        ]
        
        for crossing_data in sample_crossings:
            crossing = Crossing(**crossing_data)
            db.session.add(crossing)
        
        # Create initial meta record
        meta = Meta()
        db.session.add(meta)
        
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize database and create admin user')
    parser.add_argument('--password', '-p', help='Admin password (will prompt if not provided)')
    args = parser.parse_args()
    
    init_db(args.password) 