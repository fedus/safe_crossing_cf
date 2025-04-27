from app import create_app, db
from sqlalchemy import Column, String, Text, inspect

def manual_migration():
    app = create_app()
    with app.app_context():
        # Check if columns already exist
        inspector = inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('city')]
        
        engine = db.engine
        
        # Add icon_url column if it doesn't exist
        if 'icon_url' not in columns:
            print("Adding icon_url column to city table...")
            engine.execute('ALTER TABLE city ADD COLUMN icon_url VARCHAR(255);')
            print("Added icon_url column.")
        else:
            print("icon_url column already exists.")
            
        # Add subtitle column if it doesn't exist
        if 'subtitle' not in columns:
            print("Adding subtitle column to city table...")
            engine.execute('ALTER TABLE city ADD COLUMN subtitle VARCHAR(255);')
            print("Added subtitle column.")
        else:
            print("subtitle column already exists.")
        
        # Verify the changes
        columns_after = [column['name'] for column in inspector.get_columns('city')]
        print("City table columns after migration:", columns_after)

if __name__ == '__main__':
    manual_migration() 