# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /build

COPY pyproject.toml .

RUN uv pip install --system --no-cache ".[bot]"

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.13-slim

RUN useradd -m -u 1000 charlotte && \
    mkdir -p /app/storage/temp /app/storage/cookies /app/logs && \
    chown -R charlotte:charlotte /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

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
COPY --chown=charlotte:charlotte alembic/ alembic/
COPY --chown=charlotte:charlotte alembic.ini .
COPY --chown=charlotte:charlotte main.py .

USER charlotte

CMD ["python", "main.py"]
