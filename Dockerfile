FROM python:3.11-slim

# Create user with consistent UID/GID
RUN useradd -m -u 1000 charlotte && \
    mkdir -p /app /app/storage/temp /app/logs /app/storage/cookies && \
    chown -R charlotte:charlotte /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    gosu \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno for yt-dlp EJS
RUN curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno

ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

# Copy requirements and install
COPY --chown=charlotte:charlotte requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gallery-dl
RUN pip install -U --pre "yt-dlp[default]"

COPY --chown=charlotte:charlotte . .
RUN chmod +x /app/entrypoint.sh

# Volumes for persistence
VOLUME ["/app/storage", "/app/logs"]

ENTRYPOINT ["/app/entrypoint.sh"]
