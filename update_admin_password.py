import argparse
import getpass
import os
import sys
from app import create_app, db
from app.models.models import User

def update_admin_password(password=None, username='admin'):
    """Update a user's password.
    
    Args:
        password: Optional password to set. If not provided, will prompt for input.
        username: Username to update (defaults to 'admin')
    """
    app = create_app()
    with app.app_context():
        # Get the user
        user = User.query.get(username)
        if not user:
            print(f"User '{username}' not found!")
            return False

        # Get password from environment variable, argument, or prompt
        if not password:
            password = os.getenv('ADMIN_PASSWORD')
        
        if not password:
            while True:
                password = getpass.getpass(f"Enter new password for {username}: ")
                confirm = getpass.getpass("Confirm new password: ")
                if password == confirm:
                    break
                print("Passwords do not match. Please try again.")

        # Set new password
        user.set_password(password)
        db.session.commit()
        print(f"{username}'s password updated successfully!")
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update user password')
    parser.add_argument('--username', '-u', default='admin', help='Username to update (default: admin)')
    parser.add_argument('--password', '-p', help='New password (will prompt if not provided)')
    args = parser.parse_args()
    
    if not update_admin_password(args.password, args.username):
        sys.exit(1) 