import os
from app import create_app

# Force loading .env file
from dotenv import load_dotenv
load_dotenv(override=True)

# Print the current database URL being used
print("DATABASE_URL from env:", os.getenv("DATABASE_URL", "NOT FOUND"))

# Create the app and print its config
app = create_app()
print("SQLALCHEMY_DATABASE_URI from app:", app.config.get("SQLALCHEMY_DATABASE_URI"))

# Test if database directory is writable
db_path = app.config.get("SQLALCHEMY_DATABASE_URI", "").replace("sqlite:///", "")
if db_path.startswith("/"):
    # Absolute path
    dir_path = os.path.dirname(db_path)
else:
    # Relative path
    dir_path = os.path.dirname(os.path.join(os.getcwd(), db_path))

print("Database directory:", dir_path)
print("Directory exists:", os.path.exists(dir_path))
print("Directory is writable:", os.access(dir_path, os.W_OK))

# Try to create a test file in that directory
try:
    test_file = os.path.join(dir_path, "test_write_access.txt")
    with open(test_file, "w") as f:
        f.write("test")
    print("Successfully wrote test file:", test_file)
    os.remove(test_file)
    print("Successfully removed test file")
except Exception as e:
    print("Error writing to directory:", str(e)) 