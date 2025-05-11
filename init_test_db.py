#!/usr/bin/env python3
import os
import sys
from app import create_app, db
from app.models.models import User, City, CityVersion, Crossing, Vote

def initialize_test_database():
    """Initialize the test database with sample data."""
    print("Initializing test database...")
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if data already exists
        if City.query.count() > 0:
            print("Database already has data. Skipping initialization.")
            return
        
        # Create test user
        user = User(id='test-user-uuid')
        db.session.add(user)
        
        # Create test city
        city = City(
            name='Test City',
            description='Test city description',
            information_text='Test info',
            is_active=True,
            subtitle="Test subtitle",
            icon_url="test_icon.png"
        )
        db.session.add(city)
        db.session.flush()
        
        # Create test city version
        version = CityVersion(
            city_id=city.id,
            version_number=1,
            description='Test version',
            is_active=True
        )
        db.session.add(version)
        db.session.flush()
        
        # Create test crossings with varying vote counts
        for i in range(10):
            crossing = Crossing(
                id=f'node/{i}',
                city_id=city.id,
                version_id=version.id,
                lat=1.0 + (i * 0.001),
                lon=1.0 + (i * 0.001),
                neighbourhood='Test Neighbourhood',
                street='Test Street'
            )
            db.session.add(crossing)
        
        db.session.commit()
        
        # Add votes to crossings
        crossings = Crossing.query.all()
        
        # Add 6 votes to first crossing
        add_votes(crossings[0].id, 6, vote_type=1)  # OK votes
        
        # Add 5 votes to second crossing
        add_votes(crossings[1].id, 5, vote_type=2)  # Too close votes
        
        # Add 7 votes to third crossing
        add_votes(crossings[2].id, 7, vote_type=0)  # Not sure votes
        
        # Add 1-3 votes to the rest
        for i in range(3, 10):
            add_votes(crossings[i].id, i % 3 + 1, vote_type=i % 3)
        
        db.session.commit()
        
        print("Test database initialized successfully!")
        print(f"Created 1 city, 1 version, 10 crossings with various votes")

def add_votes(crossing_id, count, vote_type=1):
    """Helper to add votes to a crossing"""
    for i in range(count):
        user_id = f'user-{crossing_id}-{i}'  # Create unique user IDs
        user = User(id=user_id)
        db.session.add(user)
        
        vote = Vote(
            user_id=user_id,
            crossing_id=crossing_id,
            vote=vote_type  # 0: Not sure, 1: OK, 2: Too close
        )
        db.session.add(vote)
        
        # Update crossing vote counts
        crossing = Crossing.query.get(crossing_id)
        crossing.votes_total += 1
        
        if vote_type == 0:
            crossing.votes_not_sure += 1
        elif vote_type == 1:
            crossing.votes_ok += 1
        elif vote_type == 2:
            crossing.votes_too_close += 1

if __name__ == "__main__":
    initialize_test_database() 