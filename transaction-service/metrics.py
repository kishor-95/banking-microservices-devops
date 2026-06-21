"""
metrics.py - Prometheus metrics for transaction-service
Tracks: deposits, withdrawals, transaction volumes
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# ── Service Info ──────────────────────────────────────────────────────────────
SERVICE_INFO = Info('transaction_service', 'Transaction service information')

# ── Request Metrics ───────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    'transaction_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'transaction_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUESTS_IN_PROGRESS = Gauge(
    'transaction_http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# ── Business Metrics ──────────────────────────────────────────────────────────
TRANSACTIONS_PROCESSED = Counter(
    'transaction_processed_total',
    'Total transactions processed',
    ['type', 'status']  # type: DEPOSIT, WITHDRAW; status: success, failure, insufficient_funds
)

TRANSACTION_VOLUME = Counter(
    'transaction_volume_usd',
    'Total transaction volume in USD',
    ['type']  # DEPOSIT, WITHDRAW
)

TRANSACTION_AMOUNT = Histogram(
    'transaction_amount_usd',
    'Transaction amount distribution',
    ['type'],
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000]
)

TRANSACTION_ERRORS = Counter(
    'transaction_errors_total',
    'Transaction errors',
    ['error_type']  # insufficient_funds, account_not_found, account_inactive, db_error
)

# ── Database Metrics ──────────────────────────────────────────────────────────
DB_CONNECTION_ERRORS = Counter(
    'transaction_db_connection_errors_total',
    'Total database connection errors'
)

DB_QUERY_DURATION = Histogram(
    'transaction_db_query_duration_seconds',
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
def record_transaction(txn_type: str, status: str, amount: float):
    """Record transaction metric"""
    TRANSACTIONS_PROCESSED.labels(type=txn_type, status=status).inc()
    TRANSACTION_VOLUME.labels(type=txn_type).inc(amount)
    TRANSACTION_AMOUNT.labels(type=txn_type).observe(amount)


def record_transaction_error(error_type: str):
    """Record transaction error"""
    TRANSACTION_ERRORS.labels(error_type=error_type).inc()
