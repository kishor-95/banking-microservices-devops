# ── auth-service Dockerfile ─────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install OS-level deps needed for psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user (security best practice)
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8001

# Stateless — multiple replicas are safe
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
