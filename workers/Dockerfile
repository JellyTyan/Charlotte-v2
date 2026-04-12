FROM python:3.14-slim

RUN useradd -m -u 1000 charlotte && \
    mkdir -p /app /app/storage/temp /app/logs /app/storage/cookies && \
    chown -R charlotte:charlotte /app

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    gosu \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

RUN pip install uv

COPY --chown=charlotte:charlotte pyproject.toml .

RUN uv pip install --system --prerelease=allow -e .[worker]

RUN mkdir -p /home/charlotte/.config/yt-dlp && \
    echo "--remote-components ejs:npm" > /home/charlotte/.config/yt-dlp/config && \
    chown -R charlotte:charlotte /home/charlotte/.config

COPY --chown=charlotte:charlotte . .

RUN chmod +x /app/workers/entrypoint.sh
VOLUME ["/app/storage", "/app/logs"]

ENTRYPOINT ["/app/workers/entrypoint.sh"]