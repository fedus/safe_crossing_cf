#!/bin/bash
set -e

# Change ownership of mounted volumes to appuser
# This ensures the non-root user can write to the DB file
chown -R appuser:appuser /app/instance
chown -R appuser:appuser /app/logs

# Wait for potential database to be ready if using external DB (run check as appuser)
if [ ! -z "$DATABASE_URL" ] && [[ ! "$DATABASE_URL" =~ "sqlite" ]]; then
    echo "Waiting for database to be ready..."
    MAX_RETRIES=30
    RETRY_INTERVAL=2
    for i in $(seq 1 $MAX_RETRIES); do
        gosu appuser flask db current &>/dev/null && break # Run check as appuser
        echo "Database not ready yet. Retry $i of $MAX_RETRIES..."
        sleep $RETRY_INTERVAL
    done
fi

# Run database migrations as appuser
echo "Running database migrations..."
gosu appuser flask db upgrade # Run as appuser

# Create admin user if it doesn't exist (run checks/creation as appuser)
echo "Checking for admin user..."
gosu appuser python -c "from app import create_app, db; from app.models.models import User; app = create_app(); app.app_context().push(); admin = User.query.get('admin'); exit(0 if admin else 1)" || \
gosu appuser python -c "from app import create_app, db; from app.models.models import User; import os; app = create_app(); app.app_context().push(); admin = User(id='admin', is_admin=True); admin_password = os.getenv('ADMIN_PASSWORD'); if not admin_password: print('WARNING: No ADMIN_PASSWORD set. Set a secure password immediately!'); admin_password = 'CHANGE_ME_IMMEDIATELY'; admin.set_password(admin_password); db.session.add(admin); db.session.commit(); print('Admin user created');"

# Execute the CMD from the Dockerfile as appuser
# The original CMD is passed as arguments "$@"
echo "Executing command: $@"
exec gosu appuser "$@" # Run the main process as appuser 