# ── Stage 1: build dependencies ───────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build wheels (faster installs later)
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels


# ── Stage 2: runtime (clean image) ────────────────────────────
FROM python:3.12-slim


# Declare ARGs in this stage
ARG BUILD_DATE
ARG GIT_COMMIT
ARG IMAGE_TAG

LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.revision=$GIT_COMMIT \
      org.opencontainers.image.version=$IMAGE_TAG

WORKDIR /app

# Only runtime deps (no gcc here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies from wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Create user BEFORE copy (avoids chown)
RUN adduser --disabled-password --gecos "" appuser

# Copy app with correct ownership
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8002

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s  --retries=3 \
  CMD curl -f http://localhost:8002/accounts/health || exit 1

# Production-ready uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "2"]
