"""
balance-service — FastAPI
Endpoints:
  GET /balance/health          liveness probe
  GET /balance/{account_id}    single account balance (ownership enforced)
  GET /balance                 all active balances for authenticated user
"""

import os
import sys
import logging

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

# ── Metrics (NEW) ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.metrics import setup_metrics, BALANCE_QUERIES

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("balance-service")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"

app = FastAPI(title="BankApp · Balance Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# ── Prometheus setup (NEW) ────────────────────────────────────────────────────
setup_metrics(app, service_name="balance-service")

security = HTTPBearer()


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        return {"user_id": int(payload["sub"]), "username": payload["username"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/balance/health")
def health():
    return {"status": "ok", "service": "balance-service"}


@app.get("/balance/{account_id}")
def get_balance(account_id: int, user=Depends(get_current_user)):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.id, a.account_number, a.account_type, a.balance,
                   a.is_active, a.created_at, u.username, u.full_name
            FROM accounts a JOIN users u ON u.id = a.user_id
            WHERE a.id = %s
            """,
            (account_id,),
        )
        account = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as exc:
        log.error("get_balance error: %s", exc)
        BALANCE_QUERIES.labels(query_type="single", status="db_error").inc()  # NEW
        raise HTTPException(status_code=500, detail="Database error")

    if not account:
        BALANCE_QUERIES.labels(query_type="single", status="not_found").inc()  # NEW
        raise HTTPException(status_code=404, detail="Account not found")
    if account["username"] != user["username"]:
        BALANCE_QUERIES.labels(query_type="single", status="denied").inc()  # NEW
        raise HTTPException(status_code=403, detail="Access denied")
    if not account["is_active"]:
        BALANCE_QUERIES.labels(query_type="single", status="inactive").inc()  # NEW
        raise HTTPException(status_code=403, detail="Account is inactive")

    BALANCE_QUERIES.labels(query_type="single", status="success").inc()  # NEW
    return {
        "account_id": account["id"],
        "account_number": account["account_number"],
        "account_type": account["account_type"],
        "balance": float(account["balance"]),
        "owner": account["full_name"] or account["username"],
        "fetched_at": account["created_at"],
    }


@app.get("/balance")
def get_all_balances(user=Depends(get_current_user)):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, account_number, account_type, balance, is_active, created_at
            FROM accounts WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
            """,
            (user["user_id"],),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as exc:
        log.error("get_all_balances error: %s", exc)
        BALANCE_QUERIES.labels(query_type="all", status="db_error").inc()  # NEW
        raise HTTPException(status_code=500, detail="Database error")

    BALANCE_QUERIES.labels(query_type="all", status="success").inc()  # NEW
    return [
        {
            "account_id": r["id"],
            "account_number": r["account_number"],
            "account_type": r["account_type"],
            "balance": float(r["balance"]),
        }
        for r in rows
    ]
