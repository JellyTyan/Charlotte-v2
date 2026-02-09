#!/bin/bash
set -e

# Fix permissions for mounted volumes
chown -R charlotte:charlotte /app/logs /app/storage

# Start worker (as user charlotte)
echo "Starting worker with command: $@"
exec gosu charlotte "$@"
