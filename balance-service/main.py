import os
import logging
import time

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from metrics import (
    REQUEST_COUNT, REQUEST_LATENCY, REQUESTS_IN_PROGRESS,
    record_balance_query, metrics_endpoint
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("balance-service")

# ── Config ────────────────────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"
# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="BankApp · Balance Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[
                   "*"], allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer(auto_error=False)

# ── Metrics Middleware ─────────────────────────────────────────────────────────


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics"""
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    path = request.url.path
    REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).inc()

    start_time = time.time()
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)
        REQUEST_COUNT.labels(method=method, endpoint=path, status_code=status_code).inc()
        REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).dec()

    return response


# ── Metrics Endpoint ───────────────────────────────────────────────────────────
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return await metrics_endpoint()

# ── Helpers ───────────────────────────────────────────────────────────────────


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials,
                             JWT_SECRET, algorithms=[JWT_ALGO])
        return {"user_id": int(payload["sub"]), "username": payload["username"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/balance/health")
def health():
    return {"status": "ok", "service": "balance-service"}


@app.get("/balance/{account_id}")
def get_balance(account_id: int, user=Depends(get_current_user)):
    """
    Returns balance for the given account_id.
    Enforces ownership — user can only see their own accounts.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.id, a.account_number, a.account_type, a.balance,
                   a.is_active, a.created_at,
                   u.username, u.full_name
            FROM accounts a
            JOIN users u ON u.id = a.user_id
            WHERE a.id = %s
            """,
            (account_id,),
        )
        account = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as exc:
        log.error("get_balance error: %s", exc)
        record_balance_query('error')
        raise HTTPException(status_code=500, detail="Database error")

    if not account:
        record_balance_query('not_found')
        raise HTTPException(status_code=404, detail="Account not found")

    # Ownership check — never expose another user's balance
    if account["username"] != user["username"]:
        record_balance_query('access_denied')
        raise HTTPException(status_code=403, detail="Access denied")

    if not account["is_active"]:
        raise HTTPException(status_code=403, detail="Account is inactive")

    record_balance_query('success')
    return {
        "account_id":     account["id"],
        "account_number": account["account_number"],
        "account_type":   account["account_type"],
        "balance":        float(account["balance"]),
        "owner":          account["full_name"] or account["username"],
        "fetched_at":     account["created_at"],
    }


@app.get("/balance")
def get_all_balances(user=Depends(get_current_user)):
    """Return balances for all accounts belonging to the authenticated user."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, account_number, account_type, balance, is_active, created_at
            FROM accounts
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
            """,
            (user["user_id"],),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as exc:
        log.error("get_all_balances error: %s", exc)
        record_balance_query('error')
        raise HTTPException(status_code=500, detail="Database error")

    record_balance_query('success')
    return [
        {
            "account_id":     r["id"],
            "account_number": r["account_number"],
            "account_type":   r["account_type"],
            "balance":        float(r["balance"]),
        }
        for r in rows
    ]
