from app import create_app, db
import os

def update_cities_sql():
    # Create app with explicit database path
    os.environ['DATABASE_URL'] = 'sqlite:///instance/safe_crossing.db'
    app = create_app()
    with app.app_context():
        # Check if Hamburg exists
        hamburg = db.session.execute("SELECT id FROM city WHERE name='Hamburg'").fetchone()
        
        if hamburg:
            # Update Hamburg
            db.session.execute(
                "UPDATE city SET icon_url=:icon_url, subtitle=:subtitle WHERE name='Hamburg'",
                {
                    "icon_url": "https://img.icons8.com/color/48/000000/castle.png",
                    "subtitle": "City of bridges and crossings."
                }
            )
            print("Updated Hamburg")
        else:
            # Insert Hamburg
            db.session.execute(
                "INSERT INTO city (name, description, information_text, icon_url, subtitle, is_active) "
                "VALUES (:name, :description, :information_text, :icon_url, :subtitle, :is_active)",
                {
                    "name": "Hamburg",
                    "description": "Hamburg is a major port city in northern Germany.",
                    "information_text": "<p>Hamburg, the second-largest city in Germany, is home to numerous crossings and bridges.</p>",
                    "icon_url": "https://img.icons8.com/color/48/000000/castle.png",
                    "subtitle": "City of bridges and crossings.",
                    "is_active": True
                }
            )
            print("Created Hamburg")
        
        # Update Luxembourg
        luxembourg = db.session.execute("SELECT id FROM city WHERE name='Luxembourg'").fetchone()
        if luxembourg:
            db.session.execute(
                "UPDATE city SET icon_url=:icon_url, subtitle=:subtitle WHERE name='Luxembourg'",
                {
                    "icon_url": "https://img.icons8.com/color/48/000000/luxembourg.png",
                    "subtitle": "In the heart of Europe."
                }
            )
            print("Updated Luxembourg")
        else:
            print("Luxembourg not found")
        
        db.session.commit()

if __name__ == '__main__':
    update_cities_sql() 