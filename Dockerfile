# ── Build stage ────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the application (non-editable) plus all runtime dependencies.
# Non-editable avoids the editable-install finder pointing at a build-only path.
COPY pyproject.toml ./
COPY README.md ./
COPY app/ ./app/
RUN pip install --no-cache-dir --user .

# ── Runtime stage ──────────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appgroup && useradd --uid 1000 --gid 1000 --shell /bin/bash appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup . .
# /app itself is root-owned (created by WORKDIR); the beat scheduler writes
# celerybeat-schedule here, so hand it to the app user.
RUN chown appuser:appgroup /app

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
