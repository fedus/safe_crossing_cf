# Safe Crossing API Documentation

## Base URL

All API endpoints are relative to the base URL: `http://localhost:5001` (or your configured server)

## Authentication

The API does not currently require authentication tokens. User identification is handled through UUID values passed in requests.

## Data Models

### User
- `id` (String): UUID for user identification
- `initialized` (Boolean): Whether the user has been initialized
- `total_votes_cast` (Integer): Number of votes cast by the user
- `is_admin` (Boolean): Admin status
- `created_at` (DateTime): Time when the user was created

### City
- `id` (Integer): City identifier
- `name` (String): Name of the city
- `description` (Text): Description of the city
- `is_active` (Boolean): Whether the city is active
- `created_at` (DateTime): Time when the city was created
- `updated_at` (DateTime): Time when the city was last updated

### CityVersion
- `id` (Integer): Version identifier
- `city_id` (Integer): Reference to the city
- `version_number` (Integer): Version number
- `is_active` (Boolean): Whether the version is active
- `is_completed` (Boolean): Whether the version is completed
- `description` (Text): Description of the version
- `created_at` (DateTime): Time when the version was created
- `updated_at` (DateTime): Time when the version was last updated

### Crossing
- `id` (String): OSM node ID for the crossing
- `city_id` (Integer): Reference to the city
- `version_id` (Integer): Reference to the city version
- `lat` (Float): Latitude coordinate
- `lon` (Float): Longitude coordinate
- `neighbourhood` (String): Neighbourhood name
- `street` (String): Street name
- `votes_not_sure` (Integer): Count of "Not Sure" votes
- `votes_ok` (Integer): Count of "OK" votes
- `votes_too_close` (Integer): Count of "Too Close" votes
- `votes_total` (Integer): Total number of votes
- `current_result` (Integer): Current assessment result (0: Not Sure, 1: OK, 2: Too Close, 3: Tie)
- `created_at` (DateTime): Time when the crossing was created
- `updated_at` (DateTime): Time when the crossing was last updated

### Vote
- `id` (Integer): Vote identifier
- `user_id` (String): Reference to the user UUID
- `crossing_id` (String): Reference to the crossing
- `vote` (Integer): Vote value (0: Not Sure, 1: OK, 2: Too Close)
- `created_at` (DateTime): Time when the vote was cast
- `updated_at` (DateTime): Time when the vote was last updated

### Meta
- `id` (Integer): Meta record identifier
- `crossings_with_enough_votes` (Integer): Count of crossings with 5+ votes
- `votes_not_sure` (Integer): Count of crossings with "Not Sure" result
- `votes_ok` (Integer): Count of crossings with "OK" result
- `votes_too_close` (Integer): Count of crossings with "Too Close" result
- `votes_tie` (Integer): Count of crossings with "Tie" result
- `updated_at` (DateTime): Time when the meta record was last updated

## API Endpoints

### User Management

#### Initialize User
- **URL:** `/api/initialize-user`
- **Method:** `POST`
- **Description:** Creates a new user or initializes an existing one
- **Request Body:**
  ```json
  {
    "userUuid": "string"  // UUID for the user
  }
  ```
- **Response:**
  ```json
  {
    "status": "USER_INITIALIZED"
  }
  ```
  or
  ```json
  {
    "status": "USER_ALREADY_INITIALIZED"
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: If userUuid is missing
  ```json
  {
    "error": "userUuid is required"
  }
  ```

#### Get User Votes
- **URL:** `/api/votes/<user_uuid>`
- **Method:** `GET`
- **Description:** Retrieves all votes cast by a specific user
- **URL Parameters:**
  - `user_uuid`: UUID of the user
- **Response:**
  ```json
  [
    {
      "crossing_id": "string",
      "vote": 0,  // 0: Not sure, 1: OK, 2: Too close
      "created_at": "ISO-8601 timestamp"
    }
  ]
  ```

### Voting

#### Cast Vote
- **URL:** `/api/vote`
- **Method:** `POST`
- **Description:** Records a user's vote for a crossing
- **Request Body:**
  ```json
  {
    "userUuid": "string",         // UUID for the user
    "crossingNodeId": "string",   // ID of the crossing
    "vote": 0,                    // 0: Not sure, 1: OK, 2: Too close
    "city_id": 1,                 // (Optional) City ID
    "version_id": 1               // (Optional) Version ID
  }
  ```
- **Response:**
  ```json
  {
    "status": "VOTE_RECORDED",
    "new_result": 0               // 0: Not sure, 1: OK, 2: Too close, 3: Tie
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: If required parameters are missing
  ```json
  {
    "error": "Missing required parameters"
  }
  ```
  - `404 Not Found`: If crossing does not exist
  ```json
  {
    "error": "Crossing not found"
  }
  ```

### Crossings

#### Get All Crossings
- **URL:** `/api/crossings`
- **Method:** `GET`
- **Description:** Returns all crossings in the database
- **Response:**
  ```json
  [
    {
      "id": "string",
      "city": "object",
      "version": "object",
      "votes_not_sure": 0,
      "votes_ok": 0,
      "votes_too_close": 0,
      "votes_total": 0,
      "current_result": 0
    }
  ]
  ```

#### Get Crossing by ID
- **URL:** `/api/crossings/<crossing_id>`
- **Method:** `GET`
- **Description:** Returns a specific crossing by ID
- **URL Parameters:**
  - `crossing_id`: ID of the crossing
- **Response:**
  ```json
  {
    "id": "string",
    "city": "object",
    "version": "object",
    "votes_not_sure": 0,
    "votes_ok": 0,
    "votes_too_close": 0,
    "votes_total": 0,
    "current_result": 0
  }
  ```
- **Error Responses:**
  - `404 Not Found`: If crossing does not exist
  ```json
  {
    "error": "Crossing not found"
  }
  ```

### Cities and Versions

#### Get Active Cities
- **URL:** `/api/cities`
- **Method:** `GET`
- **Description:** Returns all active cities with their active versions
- **Response:**
  ```json
  [
    {
      "id": 1,
      "name": "string",
      "description": "string",
      "versions": [
        {
          "id": 1,
          "version_number": 1,
          "description": "string",
          "is_active": true,
          "is_completed": false
        }
      ]
    }
  ]
  ```

#### Get Simple Active Cities List
- **URL:** `/api/cities/active`
- **Method:** `GET`
- **Description:** Returns a simplified list of active cities
- **Response:**
  ```json
  [
    {
      "id": 1,
      "name": "string",
      "is_active": true
    }
  ]
  ```

#### Get Active Versions
- **URL:** `/api/versions/active`
- **Method:** `GET`
- **Description:** Returns a list of all active versions
- **Response:**
  ```json
  [
    {
      "id": 1,
      "name": "Version 1",
      "is_active": true
    }
  ]
  ```

#### Get Crossings for City Version
- **URL:** `/api/cities/<int:city_id>/versions/<int:version_id>/crossings`
- **Method:** `GET`
- **Description:** Returns all crossings for a specific city version
- **URL Parameters:**
  - `city_id`: ID of the city
  - `version_id`: ID of the version
- **Response:**
  ```json
  [
    {
      "id": "string",
      "lat": 0.0,
      "lon": 0.0,
      "neighbourhood": "string",
      "street": "string",
      "votes_not_sure": 0,
      "votes_ok": 0,
      "votes_too_close": 0,
      "votes_total": 0,
      "current_result": 0
    }
  ]
  ```

#### Get Unvoted Crossings for User
- **URL:** `/api/cities/<int:city_id>/versions/<int:version_id>/unvoted`
- **Method:** `GET`
- **Description:** Returns all crossings for a specific city version that a user has not voted on
- **URL Parameters:**
  - `city_id`: ID of the city
  - `version_id`: ID of the version
- **Query Parameters:**
  - `userUuid`: UUID of the user
- **Response:**
  ```json
  [
    {
      "id": "string",
      "lat": 0.0,
      "lon": 0.0,
      "neighbourhood": "string",
      "street": "string",
      "votes_not_sure": 0,
      "votes_ok": 0,
      "votes_too_close": 0,
      "votes_total": 0,
      "current_result": 0
    }
  ]
  ```
- **Error Responses:**
  - `400 Bad Request`: If userUuid is missing
  ```json
  {
    "error": "userUuid is required"
  }
  ```

## Vote Result Codes

The API uses the following numeric codes for vote results:

- `0`: Not Sure/Can't Say
- `1`: OK (compliant)
- `2`: Too Close (non-compliant)
- `3`: Tie (equal votes)

## Example API Calls

### Initialize a user
```bash
curl -X POST http://localhost:5001/api/initialize-user \
  -H "Content-Type: application/json" \
  -d '{"userUuid": "550e8400-e29b-41d4-a716-446655440000"}'
```

### Cast a vote
```bash
curl -X POST http://localhost:5001/api/vote \
  -H "Content-Type: application/json" \
  -d '{
    "userUuid": "550e8400-e29b-41d4-a716-446655440000",
    "crossingNodeId": "123456789",
    "vote": 1,
    "city_id": 1,
    "version_id": 1
  }'
```

### Get all crossings for a city version
```bash
curl -X GET http://localhost:5001/api/cities/1/versions/1/crossings
```

### Get unvoted crossings for a user
```bash
curl -X GET http://localhost:5001/api/cities/1/versions/1/unvoted?userUuid=550e8400-e29b-41d4-a716-446655440000
``` 