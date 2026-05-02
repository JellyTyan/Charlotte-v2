FROM python:3.13-slim

RUN useradd -m -u 1000 charlotte && \
    mkdir -p /app /app/storage/temp /app/logs /app/storage/cookies && \
    chown -R charlotte:charlotte /app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gosu \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install (bot-only deps)
RUN pip install uv
COPY --chown=charlotte:charlotte pyproject.toml .
RUN uv pip install --system -e .[bot]

# Copy project files (workers excluded — they have their own image)
COPY --chown=charlotte:charlotte core/ core/
COPY --chown=charlotte:charlotte handlers/ handlers/
COPY --chown=charlotte:charlotte keyboards/ keyboards/
COPY --chown=charlotte:charlotte locales/ locales/
COPY --chown=charlotte:charlotte middlewares/ middlewares/
COPY --chown=charlotte:charlotte models/ models/
COPY --chown=charlotte:charlotte modules/ modules/
COPY --chown=charlotte:charlotte senders/ senders/
COPY --chown=charlotte:charlotte states/ states/
COPY --chown=charlotte:charlotte storage/ storage/
COPY --chown=charlotte:charlotte tasks/ tasks/
COPY --chown=charlotte:charlotte utils/ utils/
COPY --chown=charlotte:charlotte workers/__init__.py workers/__init__.py
COPY --chown=charlotte:charlotte alembic/ alembic/
COPY --chown=charlotte:charlotte alembic.ini .
COPY --chown=charlotte:charlotte main.py .
COPY --chown=charlotte:charlotte entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

# Volumes for persistence
VOLUME ["/app/storage", "/app/logs"]

ENTRYPOINT ["/app/entrypoint.sh"]
