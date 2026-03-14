FROM python:3.13-slim

# Create user with consistent UID/GID
RUN useradd -m -u 1000 charlotte && \
    mkdir -p /app /app/storage/temp /app/logs /app/storage/cookies && \
    chown -R charlotte:charlotte /app

WORKDIR /app

# Install system dependencies (ffmpeg for heavy worker, deno for yt-dlp PO tokens)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    gosu \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno globally (needed for yt-dlp PO token provider)
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

# Copy requirements and install (worker-only deps)
COPY --chown=charlotte:charlotte requirements.worker.txt .
RUN pip install --no-cache-dir -r requirements.worker.txt
RUN pip install --no-cache-dir gallery-dl

# Force yt-dlp update by using build arg (pass --build-arg YTDLP_VERSION=$(date +%s) to force update)
ARG YTDLP_VERSION=1
RUN pip install -U --no-cache-dir --pre yt-dlp[default,curl-cffi]

# Copy only worker files (workers are self-contained)
COPY --chown=charlotte:charlotte workers/ workers/

# Copy and setup worker entrypoint
RUN chmod +x /app/workers/entrypoint.sh

# Volumes for persistence
VOLUME ["/app/storage", "/app/logs"]

ENTRYPOINT ["/app/workers/entrypoint.sh"]
