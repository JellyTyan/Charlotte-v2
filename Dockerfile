FROM python:3.11-slim

# Create user with consistent UID/GID
RUN useradd -m -u 1000 charlotte && \
    mkdir -p /app /app/storage/temp /app/logs /app/storage/cookies && \
    chown -R charlotte:charlotte /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    # gallery-dl often requires git if installing from source or specific system deps, but
    # pip install is usually enough. Just in case it needs more:
    git \
    gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY --chown=charlotte:charlotte requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install gallery-dl (if not in requirements.txt, but it should be. If not, uncomment next line)
RUN pip install --no-cache-dir gallery-dl

COPY --chown=charlotte:charlotte . .
RUN chmod +x /app/entrypoint.sh

# User context is now handled in entrypoint.sh using gosu
# USER charlotte

# Volumes for persistence
VOLUME ["/app/storage", "/app/logs"]

ENTRYPOINT ["/app/entrypoint.sh"]
