from app import create_app, db
from app.models.models import User

def update_admin_password():
    app = create_app()
    with app.app_context():
        # Get the admin user
        admin = User.query.get('admin')
        if admin:
            # Set new password
            admin.set_password('admin123')  # You can change this password
            db.session.commit()
            print("Admin password updated successfully!")
        else:
            print("Admin user not found!")

if __name__ == '__main__':
    update_admin_password() 