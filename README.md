# Safe Crossing API Documentation

## Project Overview

Safe Crossing is a crowdsourced initiative aimed at assessing pedestrian crossings in Luxembourg-City for compliance with safety standards. The project specifically focuses on analyzing whether parking spots are located within five meters of pedestrian crossings, which is prohibited according to the Code de la Route (Highway Code).

### Key Results
- 1,787 pedestrian crossings analyzed
- 475 (27%) crossings likely in violation of the Code de la Route
- 162 (9%) crossings with no possible assessment
- 1,150 (64%) crossings assessed as compliant

### Project Background
The project was launched in response to ongoing safety concerns for pedestrians in Luxembourg-City. Despite previous audits on pedestrian security in 2015, many crossings remained non-compliant with safety regulations. The initiative gained significant media attention and prompted discussions about urban safety and transparency in city governance.

### Data Collection Process
- Data was collected from June to August 2021
- Approximately 20 active volunteers participated
- Each crossing received at least 5 votes to ensure robust assessment
- Volunteers used a custom mobile application with satellite imagery
- Distance measurements were made using a 5-meter radius tool
- Three possible assessments:
  - Compliant (no parking within 5 meters)
  - Non-compliant (parking within 5 meters)
  - Unable to assess (e.g., due to visibility issues)

### Legal Basis
The project is based on Articles 164(2.)(e) and 166(h) of the Code de la Route, which prohibit parking within 5 meters of pedestrian crossings. The Ministry of Mobility and Public Works (MMTP) has confirmed that while parking spots may exist near crossings, parking on them is prohibited.

### Data Sources
- Pedestrian crossing locations: OpenStreetMap
- Satellite imagery: Geoportail (2020 Ortho-Photos)

### Disclaimer
This is a crowdsourced effort. While the data has been collected and processed with care, no absolute guarantees can be made regarding its accuracy. Users should verify information independently before making decisions based on this data.

## Base URL

All API endpoints are relative to the base URL: `http://localhost:5001`

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

### Crossings

#### Get All Crossings
- **URL:** `/api/crossings`
- **Method:** `GET`
- **Description:** Retrieves all crossings in the database
- **Response:**
  ```json
  [
    {
      "id": "string",
      "city": "string",
      "version": "number",
      "votes_not_sure": "number",
      "votes_ok": "number",
      "votes_too_close": "number",
      "votes_total": "number",
      "current_result": "number"  // 0: CANT_SAY, 1: OK, 2: PARKING_CLOSE, 3: TIE
    }
  ]
  ```

#### Get Single Crossing
- **URL:** `/api/crossings/<crossing_id>`
- **Method:** `GET`
- **Description:** Retrieves information about a specific crossing
- **Response:**
  ```json
  {
    "id": "string",
    "city": "string",
    "version": "number",
    "votes_not_sure": "number",
    "votes_ok": "number",
    "votes_too_close": "number",
    "votes_total": "number",
    "current_result": "number"  // 0: CANT_SAY, 1: OK, 2: PARKING_CLOSE, 3: TIE
  }
  ```
- **Error Responses:**
  - `404 Not Found`: If crossing_id does not exist
  ```json
  {
    "error": "Crossing not found"
  }
  ```

### Voting

#### Cast a Vote
- **URL:** `/api/vote`
- **Method:** `POST`
- **Description:** Records a user's vote for a specific crossing
- **Request Body:**
  ```json
  {
    "userUuid": "string",
    "crossingNodeId": "string",
    "vote": "number"  // 0: Not sure, 1: OK, 2: Too close
  }
  ```
- **Response:**
  ```json
  {
    "status": "VOTE_RECORDED",
    "new_result": "number"  // 0: CANT_SAY, 1: OK, 2: PARKING_CLOSE, 3: TIE
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: If any required parameter is missing
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

## Vote Values

- `0`: Not sure
- `1`: OK (Compliant)
- `2`: Too close (Non-compliant)

## Result Values

- `0`: CANT_SAY (Not sure)
- `1`: OK (Compliant)
- `2`: PARKING_CLOSE (Non-compliant)
- `3`: TIE

## Example Usage

### Initialize a User

```bash
curl -X POST http://localhost:5001/api/initialize-user \
  -H "Content-Type: application/json" \
  -d '{"userUuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}'
```

### Cast a Vote

```bash
curl -X POST http://localhost:5001/api/vote \
  -H "Content-Type: application/json" \
  -d '{
    "userUuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "crossingNodeId": "node1",
    "vote": 1
  }'
```

### Get All Crossings

```bash
curl -X GET http://localhost:5001/api/crossings
```

### Get User Votes

```bash
curl -X GET http://localhost:5001/api/votes/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

## Testing the API

You can use the provided `populate_test_data.py` script to automatically populate the database with test data:

```bash
python populate_test_data.py --votes 5
```

The script initializes test users and casts random votes for each crossing in the database. The `--votes` parameter specifies how many votes to cast per crossing. 