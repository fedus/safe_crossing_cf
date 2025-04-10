import requests
import uuid
import random
import argparse
from typing import List, Dict, Any
import time
import sys

BASE_URL = 'http://localhost:5001'  # Updated port to match your Flask server

def get_cities() -> List[Dict[str, Any]]:
    """Get list of existing cities from the public API."""
    try:
        # We'll use the root endpoint that gets active cities for the index page
        response = requests.get(f'{BASE_URL}/')
        response.raise_for_status()
        # Since this returns HTML, we can't parse it as JSON directly
        # The /crossings endpoint returns city information though
        return get_cities_from_crossings()
    except requests.exceptions.HTTPError as e:
        print(f"Error getting cities: {e}")
        print(f"Response: {response.text}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to the server at {BASE_URL}")
        print("Please make sure the Flask server is running.")
        sys.exit(1)

def get_cities_from_crossings() -> List[Dict[str, Any]]:
    """Extract city information from the crossings endpoint."""
    try:
        response = requests.get(f'{BASE_URL}/crossings')
        response.raise_for_status()
        
        crossings = response.json()
        
        # Extract unique cities with their active versions
        cities = {}
        for crossing in crossings:
            city_id = crossing['city_id']
            if city_id not in cities:
                cities[city_id] = {
                    'id': city_id,
                    'name': crossing['city_name'],
                    'versions': [
                        {
                            'id': crossing['version_id'],
                            'version_number': crossing['version'],
                            'is_active': True
                        }
                    ]
                }
                
        return list(cities.values())
    except requests.exceptions.HTTPError as e:
        print(f"Error getting crossings: {e}")
        print(f"Response: {response.text}")
        sys.exit(1)

def initialize_user(user_uuid: str) -> None:
    """Initialize a user via the API."""
    try:
        response = requests.post(f'{BASE_URL}/api/initialize-user', json={
            'userUuid': user_uuid
        })
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error initializing user {user_uuid}: {e}")
        print(f"Response: {response.text}")
        sys.exit(1)

def cast_vote(user_uuid: str, crossing_id: str, vote: int) -> None:
    """Cast a vote via the API."""
    try:
        response = requests.post(f'{BASE_URL}/api/vote', json={
            'userUuid': user_uuid,
            'crossingNodeId': crossing_id,
            'vote': vote
        })
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        print(f"Error casting vote: {e}")
        print(f"Response: {response.text}")
        return False

def create_test_data(num_votes_per_crossing: int):
    """Create test data using the API endpoints."""
    print("Creating test data...")
    
    # Get existing cities and crossings
    cities = get_cities()
    if not cities:
        print("No cities found in the system")
        sys.exit(1)
    
    print(f"Found {len(cities)} cities")
    
    # Get all crossings
    response = requests.get(f'{BASE_URL}/crossings')
    response.raise_for_status()
    crossings = response.json()
    
    if not crossings:
        print("No crossings found in the system")
        sys.exit(1)
    
    print(f"Found {len(crossings)} crossings")
    
    # Create users
    users = []
    for i in range(3):
        user_uuid = str(uuid.uuid4())
        users.append(user_uuid)
        print(f"Initializing user {i+1}")
        initialize_user(user_uuid)
    
    # Cast random votes
    total_votes = 0
    for crossing in crossings:
        crossing_id = crossing['id']
        print(f"Processing crossing: {crossing_id}")
        
        for _ in range(num_votes_per_crossing):
            user_uuid = random.choice(users)
            vote = random.choice([0, 1, 2])  # 0: not sure, 1: ok, 2: too close
            
            print(f"  User {user_uuid[-6:]} voting {vote}")
            if cast_vote(user_uuid, crossing_id, vote):
                total_votes += 1
            time.sleep(0.1)  # Small delay to avoid overwhelming the server
    
    # Test error cases
    print("\nTesting error cases...")
    
    # Test 1: Vote on non-existent city
    print("\nTest 1: Voting on non-existent city")
    non_existent_crossing = "non-existent-crossing-id"
    user_uuid = random.choice(users)
    print(f"  User {user_uuid[-6:]} voting on non-existent crossing {non_existent_crossing}")
    cast_vote(user_uuid, non_existent_crossing, 1)
    
    # Test 2: Vote on inactive version
    print("\nTest 2: Voting on inactive version")
    # Create a crossing ID that matches the format but with an inactive version
    if crossings:
        first_crossing = crossings[0]
        inactive_version_crossing = f"{first_crossing['id']}_inactive"
        print(f"  User {user_uuid[-6:]} voting on inactive version crossing {inactive_version_crossing}")
        cast_vote(user_uuid, inactive_version_crossing, 1)
    
    print("\nTest data creation completed!")
    print(f"Created {len(users)} users")
    print(f"Successfully cast {total_votes} votes")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Populate the database with test votes')
    parser.add_argument('--votes', type=int, default=3, help='Number of votes to cast per crossing')
    
    args = parser.parse_args()
    create_test_data(args.votes) 