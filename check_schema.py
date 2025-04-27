from app import create_app, db

def check_schema():
    app = create_app()
    with app.app_context():
        # Query SQLite directly for table schema
        result = db.session.execute("PRAGMA table_info(city)").fetchall()
        print("City table columns (from PRAGMA):")
        for col in result:
            print(f"- {col[1]}: {col[2]}")

if __name__ == '__main__':
    check_schema() 