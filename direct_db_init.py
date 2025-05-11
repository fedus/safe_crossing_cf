import sqlite3
import os
from datetime import datetime

# Ensure instance directory exists
os.makedirs('instance', exist_ok=True)

# Define the path to the database
db_path = 'instance/safe_crossing.db'

# Remove existing database if it exists
if os.path.exists(db_path):
    os.remove(db_path)

# Create a new database and connect to it
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Create your schema here - MATCH THE SQLALCHEMY MODELS EXACTLY
c.execute('''
CREATE TABLE user (
    id TEXT PRIMARY KEY,
    initialized BOOLEAN DEFAULT 0,
    total_votes_cast INTEGER DEFAULT 0,
    is_admin BOOLEAN DEFAULT 0,
    password_hash TEXT,
    fcm_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

c.execute('''
CREATE TABLE city (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    information_text TEXT,
    icon_url TEXT,
    subtitle TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

c.execute('''
CREATE TABLE city_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT 0,
    is_completed BOOLEAN DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES city (id),
    UNIQUE (city_id, version_number)
)
''')

c.execute('''
CREATE TABLE crossing (
    id TEXT PRIMARY KEY,
    city_id INTEGER NOT NULL,
    version_id INTEGER NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    neighbourhood TEXT,
    street TEXT,
    votes_not_sure INTEGER DEFAULT 0,
    votes_ok INTEGER DEFAULT 0,
    votes_too_close INTEGER DEFAULT 0,
    votes_total INTEGER DEFAULT 0,
    current_result INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES city (id),
    FOREIGN KEY (version_id) REFERENCES city_version (id)
)
''')

c.execute('''
CREATE TABLE vote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    crossing_id TEXT NOT NULL,
    vote INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (crossing_id) REFERENCES crossing (id),
    UNIQUE (user_id, crossing_id)
)
''')

c.execute('''
CREATE TABLE meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crossings_with_enough_votes INTEGER DEFAULT 0,
    votes_not_sure INTEGER DEFAULT 0,
    votes_ok INTEGER DEFAULT 0,
    votes_too_close INTEGER DEFAULT 0,
    votes_tie INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Insert admin user
import getpass
import hashlib
from werkzeug.security import generate_password_hash

admin_password = 'admin'  # Default password

# Using proper werkzeug password hashing
c.execute("INSERT INTO user (id, initialized, total_votes_cast, is_admin, password_hash, fcm_token) VALUES (?, ?, ?, ?, ?, ?)",
          ('admin', 1, 0, 1, generate_password_hash(admin_password), None))

# Insert sample city
c.execute("INSERT INTO city (name, description) VALUES (?, ?)",
          ('Sample City', 'A sample city for testing'))
city_id = c.lastrowid

# Insert sample version
c.execute("INSERT INTO city_version (city_id, version_number, description, is_active) VALUES (?, ?, ?, ?)",
          (city_id, 1, 'Initial version', 1))
version_id = c.lastrowid

# Insert sample crossings
sample_crossings = [
    ('node1', city_id, version_id, 49.6116, 6.1319),
    ('node2', city_id, version_id, 49.6117, 6.1320),
    ('node3', city_id, version_id, 49.6118, 6.1321)
]

for crossing in sample_crossings:
    c.execute("INSERT INTO crossing (id, city_id, version_id, lat, lon) VALUES (?, ?, ?, ?, ?)", crossing)

# Insert meta
c.execute("INSERT INTO meta DEFAULT VALUES")

# Commit and close
conn.commit()
conn.close()

# Set permissions
os.chmod(db_path, 0o666)

print(f"Database has been created at {os.path.abspath(db_path)}")
print("Admin user created with password: admin")
print("Now try restarting your Flask application and see if it can connect.") 