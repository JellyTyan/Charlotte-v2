FROM python:3.13-slim

# Create user with consistent UID/GID
RUN useradd -m -u 1000 charlotte && \
    mkdir -p /app /app/storage/temp /app/logs /app/storage/cookies && \
    chown -R charlotte:charlotte /app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    gosu \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno globally for all users
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

# Copy requirements and install
COPY --chown=charlotte:charlotte requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gallery-dl
RUN pip install -U --no-cache-dir --pre yt-dlp[default,curl-cffi]

COPY --chown=charlotte:charlotte . .
RUN chmod +x /app/entrypoint.sh

# Volumes for persistence
VOLUME ["/app/storage", "/app/logs"]

ENTRYPOINT ["/app/entrypoint.sh"]
