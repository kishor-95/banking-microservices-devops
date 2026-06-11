"""
Single source of truth for all Prometheus metrics across VaultX services.

Usage in each service main.py:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from common.metrics import setup_metrics, AUTH_REGISTRATIONS, ...

    app = FastAPI(...)
    setup_metrics(app, service_name="auth-service")
"""

from prometheus_client import Counter, Histogram, REGISTRY
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Request

# ── Safe metric creators (avoid duplicate registration errors) ────────────────


def _counter(name: str, doc: str, labels: list) -> Counter:
    try:
        return Counter(name, doc, labels)
    except ValueError:
        return REGISTRY._names_to_collectors.get(name)  # reuse existing


def _histogram(name: str, doc: str, labels: list, buckets: list) -> Histogram:
    try:
        return Histogram(name, doc, labels, buckets=buckets)
    except ValueError:
        return REGISTRY._names_to_collectors.get(name)


# ── Auth service metrics ──────────────────────────────────────────────────────

AUTH_REGISTRATIONS = _counter(
    "bankapp_auth_registrations_total",
    "User registration attempts. status=[success|failure]",
    ["status"],
)

AUTH_LOGINS = _counter(
    "bankapp_auth_logins_total",
    "Login attempts. status=[success|invalid_credentials|disabled|db_error]",
    ["status"],
)

AUTH_TOKEN_VERIFICATIONS = _counter(
    "bankapp_auth_verifications_total",
    "JWT verify calls. status=[success|expired|invalid]",
    ["status"],
)


# ── Account service metrics ───────────────────────────────────────────────────

ACCOUNTS_OPENED = _counter(
    "bankapp_accounts_opened_total",
    "Accounts opened. status=[success|failure], account_type=[checking|savings]",
    ["status", "account_type"],
)

ACCOUNTS_CLOSED = _counter(
    "bankapp_accounts_closed_total",
    "Account close attempts.",
    ["status"],
)

PROFILE_FETCHES = _counter(
    "bankapp_profile_fetches_total",
    "Profile fetch calls.",
    ["status"],
)


# ── Balance service metrics ───────────────────────────────────────────────────

BALANCE_QUERIES = _counter(
    "bankapp_balance_queries_total",
    "Balance queries.",
    ["query_type", "status"],
)


# ── Transaction service metrics ───────────────────────────────────────────────

TRANSACTIONS = _counter(
    "bankapp_transactions_total",
    "Transaction attempts.",
    ["type", "status"],
)

TRANSACTION_AMOUNT = _histogram(
    "bankapp_transaction_amount_dollars",
    "Transaction amounts in USD.",
    ["type"],
    [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, float("inf")],
)


# ── Setup function (FIXED + COMPATIBLE) ───────────────────────────────────────


def setup_metrics(app: FastAPI, service_name: str = "bankapp") -> None:
    """
    Prometheus instrumentation setup.

    - Works with prometheus-fastapi-instrumentator==6.1.0
    - Adds custom HTTP request counter with service label
    - Keeps auto metrics (latency, in-progress)
    """

    # 🔥 Custom request counter (with service label)
    REQUEST_COUNT = _counter(
        "bankapp_http_requests_total",
        "Total HTTP Requests",
        ["method", "endpoint", "status_code", "service"],
    )

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        response = await call_next(request)

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            service=service_name,
        ).inc()

        return response

    # 🔥 Default instrumentator (latency, in-progress, etc.)
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    ).instrument(app).expose(
        app,
        include_in_schema=False,
        should_gzip=False,
    )
