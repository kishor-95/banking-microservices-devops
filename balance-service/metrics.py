"""
metrics.py - Prometheus metrics for balance-service
Tracks: balance queries, request latency
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# ── Service Info ──────────────────────────────────────────────────────────────
SERVICE_INFO = Info('balance_service', 'Balance service information')

# ── Request Metrics ───────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    'balance_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'balance_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

REQUESTS_IN_PROGRESS = Gauge(
    'balance_http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# ── Business Metrics ──────────────────────────────────────────────────────────
BALANCE_QUERIES = Counter(
    'balance_queries_total',
    'Total balance query requests',
    ['status']  # success, not_found, access_denied
)

TOTAL_BALANCE_QUERIED = Counter(
    'balance_total_queried_usd',
    'Total USD amount queried'
)

# ── Database Metrics ──────────────────────────────────────────────────────────
DB_CONNECTION_ERRORS = Counter(
    'balance_db_connection_errors_total',
    'Total database connection errors'
)

DB_QUERY_DURATION = Histogram(
    'balance_db_query_duration_seconds',
    'Database query duration',
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
def record_balance_query(status: str):
    """Record balance query metric"""
    BALANCE_QUERIES.labels(status=status).inc()


def record_balance_amount(amount: float):
    """Record total balance amount queried"""
    TOTAL_BALANCE_QUERIED.inc(amount)
