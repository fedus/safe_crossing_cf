FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .
COPY add_test_data.py /app/
COPY init_db.py /app/

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV FLASK_DEBUG=False

# Create necessary directories and set permissions
RUN mkdir -p /app/instance && \
    mkdir -p /app/migrations && \
    mkdir -p /app/logs && \
    useradd -m appuser && \
    chown -R appuser:appuser /app && \
    chmod 777 /app/instance /app/migrations /app/logs

# Add volume for persistent data
VOLUME ["/app/instance"]

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Expose the port the app runs on
EXPOSE 5000

# Run migrations when container starts
ENTRYPOINT ["./docker-entrypoint.sh"]

# Command to run the application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "run:app"] 