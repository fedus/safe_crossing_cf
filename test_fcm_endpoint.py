import requests
import json

# Replace with your actual server URL
base_url = "http://localhost:5001"

# Test data
test_data = {
    "user_id": "admin",  # Using the admin user we created
    "fcm_token": "test_fcm_token_123456"
}

# Make the API request
response = requests.post(
    f"{base_url}/api/users/link-fcm-token",
    json=test_data
)

# Print the results
print(f"Status Code: {response.status_code}")
try:
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Response text: {response.text}") 