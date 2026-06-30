"""
metrics.py - Prometheus metrics for auth-service
Includes: request latency, error rates, business metrics (logins, registrations)
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# ── Service Info ──────────────────────────────────────────────────────────────
SERVICE_INFO = Info('auth_service', 'Auth service information')

# ── Request Metrics ───────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    'auth_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'auth_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUESTS_IN_PROGRESS = Gauge(
    'auth_http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# ── Business Metrics ──────────────────────────────────────────────────────────
LOGIN_ATTEMPTS = Counter(
    'auth_login_attempts_total',
    'Total login attempts',
    ['status']  # success, failure, invalid_credentials, account_disabled
)

REGISTRATIONS = Counter(
    'auth_registrations_total',
    'Total user registrations',
    ['status']  # success, duplicate, validation_error
)

TOKEN_OPERATIONS = Counter(
    'auth_token_operations_total',
    'Token operations (create/verify)',
    ['operation', 'status']  # operation: create, verify; status: success, failure
)

ACTIVE_USERS = Gauge(
    'auth_active_users',
    'Number of active users (logged in recently)'
)

# ── Database Metrics ──────────────────────────────────────────────────────────
DB_CONNECTION_ERRORS = Counter(
    'auth_db_connection_errors_total',
    'Total database connection errors'
)

DB_QUERY_DURATION = Histogram(
    'auth_db_query_duration_seconds',
    'Database query duration',
    ['query_type'],  # select, insert, update
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# ── Metrics Endpoint ──────────────────────────────────────────────────────────


async def metrics_endpoint():
    """Returns Prometheus-formatted metrics"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ── Helper Functions ──────────────────────────────────────────────────────────
def record_login(status: str):
    """Record login attempt metric"""
    LOGIN_ATTEMPTS.labels(status=status).inc()


def record_registration(status: str):
    """Record registration metric"""
    REGISTRATIONS.labels(status=status).inc()


def record_token_operation(operation: str, status: str):
    """Record token operation metric"""
    TOKEN_OPERATIONS.labels(operation=operation, status=status).inc()
