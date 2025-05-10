#!/usr/bin/env python3
import requests
import json
import sys

BASE_URL = 'http://localhost:5001'  # Adjust if your server runs on a different port

def test_cities_endpoint():
    """Test the updated cities endpoint that includes completion information."""
    print("\n=== Testing /api/cities endpoint ===")
    response = requests.get(f'{BASE_URL}/api/cities')
    
    if response.status_code != 200:
        print(f"Error: Got status code {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    cities = response.json()
    
    if not cities:
        print("Warning: No cities returned")
        return True
    
    print(f"Found {len(cities)} cities")
    
    # Check if completion data is present
    for city in cities:
        city_id = city['id']
        city_name = city['name']
        
        if 'completion' not in city:
            print(f"Error: City {city_name} (ID: {city_id}) missing completion data")
            return False
        
        completion = city['completion']
        required_fields = ['total_votes', 'votes_limit', 'total_crossings', 
                           'crossings_with_enough_votes', 'completion_percentage']
        
        for field in required_fields:
            if field not in completion:
                print(f"Error: City {city_name} missing '{field}' in completion data")
                return False
        
        print(f"City: {city_name}")
        print(f"  Total crossings: {completion['total_crossings']}")
        print(f"  Total votes: {completion['total_votes']}")
        print(f"  Crossings with enough votes: {completion['crossings_with_enough_votes']}")
        print(f"  Completion percentage: {completion['completion_percentage']}%")
    
    return True

def test_city_completion_endpoint():
    """Test the city completion endpoint for specific cities."""
    print("\n=== Testing /api/cities/{city_id}/completion endpoint ===")
    
    # First get list of cities to test
    response = requests.get(f'{BASE_URL}/api/cities')
    if response.status_code != 200:
        print(f"Error: Could not get cities list, status code {response.status_code}")
        return False
    
    cities = response.json()
    if not cities:
        print("Warning: No cities to test")
        return True
    
    for city in cities:
        city_id = city['id']
        city_name = city['name']
        print(f"\nTesting completion for city: {city_name} (ID: {city_id})")
        
        response = requests.get(f'{BASE_URL}/api/cities/{city_id}/completion')
        
        if response.status_code != 200:
            print(f"Error: Got status code {response.status_code}")
            print(f"Response: {response.text}")
            continue
        
        completion_data = response.json()
        
        # Verify all fields are present
        required_fields = ['city_id', 'version_id', 'total_crossings', 'total_votes',
                          'votes_limit', 'crossings_with_enough_votes', 'completion_percentage']
        
        for field in required_fields:
            if field not in completion_data:
                print(f"Error: Missing '{field}' in completion data")
                continue
        
        # Print details
        print(f"  City ID: {completion_data['city_id']}")
        print(f"  Version ID: {completion_data['version_id']}")
        print(f"  Total crossings: {completion_data['total_crossings']}")
        print(f"  Total votes: {completion_data['total_votes']}")
        print(f"  Votes limit: {completion_data['votes_limit']}")
        print(f"  Crossings with enough votes: {completion_data['crossings_with_enough_votes']}")
        print(f"  Completion percentage: {completion_data['completion_percentage']}%")
        
        # Verify data consistency
        if city['completion']['total_crossings'] != completion_data['total_crossings']:
            print("  Warning: total_crossings mismatch between endpoints")
        
        if city['completion']['total_votes'] != completion_data['total_votes']:
            print("  Warning: total_votes mismatch between endpoints")
        
        if city['completion']['crossings_with_enough_votes'] != completion_data['crossings_with_enough_votes']:
            print("  Warning: crossings_with_enough_votes mismatch between endpoints")
        
        if city['completion']['completion_percentage'] != completion_data['completion_percentage']:
            print("  Warning: completion_percentage mismatch between endpoints")
    
    return True

def main():
    print("Testing city completion functionality")
    
    # Test if server is running
    try:
        response = requests.get(f'{BASE_URL}/health')
        if response.status_code != 200:
            print(f"Server health check failed with status code {response.status_code}")
            return 1
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to server at {BASE_URL}")
        print("Please make sure the Flask server is running.")
        return 1
    
    all_succeeded = True
    
    if not test_cities_endpoint():
        all_succeeded = False
    
    if not test_city_completion_endpoint():
        all_succeeded = False
    
    if all_succeeded:
        print("\nAll tests passed!")
        return 0
    else:
        print("\nSome tests failed. Please check the output for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 