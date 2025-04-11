import requests
import json
import uuid
import random
from datetime import datetime

def add_test_data():
    # Use the service name 'web' instead of localhost since we're running inside Docker
    base_url = "http://web:5000"
    api_url = f"{base_url}/api"
    
    # Get existing crossings from the main /crossings endpoint
    print("Fetching existing crossings...")
    crossings_response = requests.get(f"{base_url}/crossings")
    if crossings_response.status_code != 200:
        print(f"Failed to get crossings: {crossings_response.text}")
        return
    
    crossings = crossings_response.json()
    if not crossings:
        print("No crossings found in the database. Make sure the database is initialized with crossings.")
        return
    
    print(f"Found {len(crossings)} crossings in the database")
    
    # Create 5 test users
    users = []
    for i in range(5):
        user_uuid = str(uuid.uuid4())
        user_data = {
            "userUuid": user_uuid
        }
        
        # Initialize user
        print(f"Initializing user {i+1}...")
        init_response = requests.post(f"{api_url}/initialize-user", json=user_data)
        if init_response.status_code != 200:
            print(f"Failed to initialize user: {init_response.text}")
            continue
        
        users.append(user_uuid)
        print(f"Created user with UUID: {user_uuid}")
    
    if not users:
        print("Failed to create any users")
        return
    
    # Cast votes for each crossing with each user
    vote_options = [0, 1, 2]  # 0: Not sure, 1: OK, 2: Too close
    votes_cast = 0
    
    for crossing in crossings:
        crossing_id = crossing['id']
        
        for user_uuid in users:
            # Randomly choose a vote
            vote_value = random.choice(vote_options)
            
            vote_data = {
                "userUuid": user_uuid,
                "crossingNodeId": crossing_id,
                "vote": vote_value
            }
            
            # Cast vote
            vote_response = requests.post(f"{api_url}/vote", json=vote_data)
            if vote_response.status_code != 200:
                print(f"Failed to cast vote for crossing {crossing_id} by user {user_uuid}: {vote_response.text}")
                continue
            
            votes_cast += 1
            print(f"Cast vote {vote_value} for crossing {crossing_id} by user {user_uuid}")
    
    print(f"Test data added successfully! Created {len(users)} users and cast {votes_cast} votes.")

if __name__ == '__main__':
    add_test_data() 