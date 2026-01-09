#!/bin/bash
set -e

# Fix permissions for mounted volumes
chown -R charlotte:charlotte /app/logs /app/storage

# Run migrations (as user charlotte)
echo "Running database migrations..."
gosu charlotte alembic upgrade head

# Start application (as user charlotte)
echo "Starting application..."
exec gosu charlotte python main.py
