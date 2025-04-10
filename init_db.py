from app import create_app, db
from app.models.models import User, City, CityVersion, Crossing, Meta

def init_db():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create admin user
        admin = User(
            id='admin',
            is_admin=True
        )
        admin.set_password('admin123')  # Change this password in production!
        db.session.add(admin)
        
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
    init_db() 