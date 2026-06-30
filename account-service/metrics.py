"""
metrics.py - Prometheus metrics for account-service
Tracks: account operations, balance metrics, request latency
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# ── Service Info ──────────────────────────────────────────────────────────────
SERVICE_INFO = Info('account_service', 'Account service information')

# ── Request Metrics ───────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    'account_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'account_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUESTS_IN_PROGRESS = Gauge(
    'account_http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# ── Business Metrics ──────────────────────────────────────────────────────────
ACCOUNTS_CREATED = Counter(
    'account_accounts_created_total',
    'Total accounts created',
    ['account_type']  # checking, savings
)

ACCOUNTS_CLOSED = Counter(
    'account_accounts_closed_total',
    'Total accounts closed'
)

ACCOUNT_OPERATIONS = Counter(
    'account_operations_total',
    'Account operations',
    ['operation', 'status']  # operation: create, close, list, profile; status: success, failure
)

ACTIVE_ACCOUNTS = Gauge(
    'account_active_accounts',
    'Number of active accounts'
)

# ── Database Metrics ──────────────────────────────────────────────────────────
DB_CONNECTION_ERRORS = Counter(
    'account_db_connection_errors_total',
    'Total database connection errors'
)

DB_QUERY_DURATION = Histogram(
    'account_db_query_duration_seconds',
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
def record_account_created(account_type: str):
    """Record account creation metric"""
    ACCOUNTS_CREATED.labels(account_type=account_type).inc()


def record_account_closed():
    """Record account closure metric"""
    ACCOUNTS_CLOSED.inc()


def record_account_operation(operation: str, status: str):
    """Record account operation metric"""
    ACCOUNT_OPERATIONS.labels(operation=operation, status=status).inc()
