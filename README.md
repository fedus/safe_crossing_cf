# Safe Crossing CF

A Flask application for managing safe crossing operations.

## Development Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

5. Run the development server:
```bash
flask run
```

## Docker Deployment

This application is fully containerized and ready for production deployment using Gunicorn as a WSGI server. Here's how to run it using Docker:

### Prerequisites

- Docker and Docker Compose installed on your system

### Quick Start

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd safe_crossing_cf
   ```

2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file to configure your environment:
   ```
   SECRET_KEY=your-secure-secret-key
   DATABASE_URL=sqlite:///instance/safe_crossing.db
   FLASK_ENV=production
   # Admin password will be prompted during first run if not set here
   ADMIN_PASSWORD=your-secure-admin-password
   ```

4. Build and start the application:
   ```bash
   docker compose up -d
   ```

5. Access the application at http://localhost:5000

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SECRET_KEY | Flask secret key for sessions | change-this-in-production |
| DATABASE_URL | Database connection URL | sqlite:///instance/safe_crossing.db |
| ADMIN_PASSWORD | Password for the admin user | (empty - will prompt during setup) |
| PORT | Port to run the application on | 5000 |
| FLASK_ENV | Flask environment | production |
| FLASK_DEBUG | Enable debug mode | false |
| FLASK_HOST | Host to bind the server to | 0.0.0.0 |
| FLASK_PORT | Port for the Flask app | 5000 |

### Database Management

The application uses Alembic for database migrations. Migrations run automatically when the container starts.

To manually run migrations or create a new migration:

```bash
# Run migrations
docker compose exec web flask db upgrade

# Create a new migration after model changes
docker compose exec web flask db migrate -m "Description of changes"
```

### Admin Password Reset

To reset the admin password:

```bash
# Interactive (will prompt for password)
docker compose exec web python update_admin_password.py
```

Or specify a new password directly:

```bash
docker compose exec web python update_admin_password.py --password new-password
```

### Production Deployment Considerations

- Use a proper database like PostgreSQL instead of SQLite
- Set a strong SECRET_KEY
- Configure proper SSL/TLS with a reverse proxy like Nginx
- Consider using Docker Swarm or Kubernetes for high availability
- The application runs with Gunicorn in production for better performance and stability

## Database Migrations

To create a new migration:
```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

To rollback a migration:
```bash
flask db downgrade
```

## Admin Password Reset

To reset the admin password:
```bash
# Interactive (will prompt for password)
python update_admin_password.py

# Or with a specific password:
python update_admin_password.py --password your_new_password

# Or using an environment variable:
ADMIN_PASSWORD=your_new_password python update_admin_password.py
```

## Database Initialization

To initialize the database:
```bash
# Interactive (will prompt for admin password)
python init_db.py

# Or with a specific admin password:
python init_db.py --password your_admin_password

# Or using an environment variable:
ADMIN_PASSWORD=your_admin_password python init_db.py
```

## Configuration

The application can be configured through environment variables:

- `FLASK_APP`: Application entry point (default: run.py)
- `FLASK_ENV`: Environment (development/production)
- `FLASK_DEBUG`: Enable debug mode (true/false)
- `SECRET_KEY`: Secret key for session management
- `DATABASE_URL`: Database connection URL
- `ADMIN_PASSWORD`: Admin user password
- `FLASK_HOST`: Host to bind the server to (default: 0.0.0.0 in Docker)
- `FLASK_PORT`: Port for the Flask app (default: 5000 in Docker)

## Security Notes

- Never commit the .env file to version control
- Use strong, unique passwords for admin accounts
- In production, always use HTTPS
- Keep dependencies updated
- Never run the application in debug mode in production

# Safe Crossing Server API Documentation

## Project Overview

Safe Crossing is a crowdsourced initiative aimed at assessing pedestrian crossings in Luxembourg-City for compliance with safety standards. The project specifically focuses on analyzing whether parking spots are located within five meters of pedestrian crossings, which is prohibited according to the Code de la Route (Highway Code).

### Project Background
The project was launched in response to ongoing safety concerns for pedestrians in Luxembourg-City. Despite previous audits on pedestrian security in 2015, many crossings remained non-compliant with safety regulations. The initiative gained significant media attention and prompted discussions about urban safety and transparency in city governance.

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

#### Get Active Cities
- **URL:** `/api/cities/active`
- **Method:** `GET`
- **Description:** Retrieves a list of all active cities
- **Response:**
  ```json
  [
    {
      "id": "string",
      "name": "string",
      "is_active": true
    }
  ]
  ```

#### Get Active Versions
- **URL:** `/api/versions/active`
- **Method:** `GET`
- **Description:** Retrieves a list of all active versions
- **Response:**
  ```json
  [
    {
      "id": "string",
      "name": "string",
      "is_active": true
    }
  ]
  ```

#### Get Crossings
- **URL:** `/api/crossings`
- **Method:** `GET`
- **Description:** Retrieves all crossings with optional filtering
- **Query Parameters:**
  - `city_id`: Filter by city ID
  - `version_id`: Filter by version ID
- **Response:**
  ```json
  [
    {
      "id": "string",
      "name": "string",
      "latitude": "float",
      "longitude": "float",
      "city_id": "string",
      "version_id": "string",
      "votes": {
        "total": 0,
        "ok": 0,
        "too_close": 0,
        "not_sure": 0
      }
    }
  ]
  ```

#### Submit Vote
- **URL:** `/api/votes`
- **Method:** `POST`
- **Description:** Submits a vote for a crossing
- **Request Body:**
  ```json
  {
    "userUuid": "string",
    "crossingId": "string",
    "vote": 0  // 0: Not sure, 1: OK, 2: Too close
  }
  ```
- **Response:**
  ```json
  {
    "status": "VOTE_RECORDED",
    "message": "Vote successfully recorded"
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: If required fields are missing or invalid
  - `404 Not Found`: If crossing or user not found
  - `409 Conflict`: If user has already voted for this crossing

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

## Admin Panel Features

The admin panel provides comprehensive management capabilities for the Safe Crossing application:

### Crossings Management
- Bulk import of crossings via CSV
- Individual crossing creation and editing
- Crossing deletion
- View crossing details including vote statistics
- Filter crossings by city and version

### User Management
- View user statistics
- Monitor user activity
- Manage user access

### Data Management
- Database migrations
- Backup and restore functionality
- Data export capabilities

## Development Status

The project is actively maintained and regularly updated with new features and improvements. Current development focuses on:

- Enhanced API documentation
- Improved data validation
- Performance optimizations
- Security enhancements
- User experience improvements

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 

## Deploy Runbook

### Prerequisites
- Docker / Docker Compose
- Volume mounted for `instance/` (SQLite DB persistence)

### One-time: resolve multiple Alembic heads (if present)
```bash
# From server repo dir
git fetch origin
git reset --hard origin/flask-docker-production

# Build fresh
docker compose down
docker compose build --no-cache

# Merge heads and upgrade (bypass entrypoint)
docker compose run --rm --entrypoint bash web -lc 'export FLASK_APP=run.py; flask db merge -m "merge heads (prod)" heads'
docker compose run --rm --entrypoint bash web -lc 'export FLASK_APP=run.py; flask db upgrade'

# Start app
docker compose up -d
```

### Normal deploy
```bash
git fetch origin
git reset --hard origin/flask-docker-production
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Skip auto-migrations on start (optional)
Set `SKIP_DB_MIGRATIONS=1` in the container env to skip automatic `flask db upgrade` in entrypoint. Useful if you want to run migrations explicitly before start.

```yaml
# docker-compose.yml example
environment:
  - FLASK_ENV=production
  - ADMIN_PASSWORD=***
  - SKIP_DB_MIGRATIONS=1
```

Then run:
```bash
docker compose run --rm --entrypoint bash web -lc 'export FLASK_APP=run.py; flask db upgrade'
docker compose up -d
``` 