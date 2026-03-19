import os
import logging
from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from pydantic import BaseModel, field_validator

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("transaction-service")

# ── Config ────────────────────────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = os.getenv("DB_PORT")
DB_NAME     = os.getenv("DB_NAME")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
JWT_SECRET  = os.getenv("JWT_SECRET")
JWT_ALGO    = "HS256"
# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="BankApp · Transaction Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer()

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_conn():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = False   # explicit transaction management
    return conn


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        return {"user_id": int(payload["sub"]), "username": payload["username"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _get_account_locked(cur, account_id: int, user_id: int):
    """
    Fetch the account row with a row-level lock.
    Also verifies ownership.
    """
    cur.execute(
        """
        SELECT a.id, a.balance, a.is_active, a.user_id
        FROM accounts a
        WHERE a.id = %s
        FOR UPDATE
        """,
        (account_id,),
    )
    account = cur.fetchone()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not account["is_active"]:
        raise HTTPException(status_code=403, detail="Account is inactive")
    return account


# ── Pydantic models ───────────────────────────────────────────────────────────
class TransactionRequest(BaseModel):
    account_id:  int
    amount:      float
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be positive")
        if round(v, 2) != v:
            raise ValueError("Amount max 2 decimal places")
        return round(v, 2)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/transactions/health")
def health():
    return {"status": "ok", "service": "transaction-service"}


@app.post("/transactions/deposit", status_code=201)
def deposit(body: TransactionRequest, user=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = conn.cursor()

        # Lock row
        account = _get_account_locked(cur, body.account_id, user["user_id"])
        new_balance = float(account["balance"]) + body.amount

        # Update balance
        cur.execute(
            "UPDATE accounts SET balance = %s WHERE id = %s",
            (new_balance, body.account_id),
        )

        # Append ledger entry
        cur.execute(
            """
            INSERT INTO transactions (account_id, type, amount, balance_after, description)
            VALUES (%s, 'DEPOSIT', %s, %s, %s)
            RETURNING id, type, amount, balance_after, created_at, reference_id
            """,
            (body.account_id, body.amount, new_balance, body.description),
        )
        txn = cur.fetchone()
        conn.commit()
        log.info("Deposit $%.2f → account %d (balance now $%.2f)", body.amount, body.account_id, new_balance)

    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        log.error("deposit error: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        conn.close()

    return {
        "transaction_id":  txn["id"],
        "reference_id":    str(txn["reference_id"]),
        "type":            txn["type"],
        "amount":          float(txn["amount"]),
        "balance_after":   float(txn["balance_after"]),
        "created_at":      txn["created_at"],
    }


@app.post("/transactions/withdraw", status_code=201)
def withdraw(body: TransactionRequest, user=Depends(get_current_user)):
    conn = get_conn()
    try:
        cur = conn.cursor()

        account = _get_account_locked(cur, body.account_id, user["user_id"])
        current_balance = float(account["balance"])

        if body.amount > current_balance:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient funds. Available: ${current_balance:.2f}",
            )

        new_balance = current_balance - body.amount

        cur.execute(
            "UPDATE accounts SET balance = %s WHERE id = %s",
            (new_balance, body.account_id),
        )
        cur.execute(
            """
            INSERT INTO transactions (account_id, type, amount, balance_after, description)
            VALUES (%s, 'WITHDRAW', %s, %s, %s)
            RETURNING id, type, amount, balance_after, created_at, reference_id
            """,
            (body.account_id, body.amount, new_balance, body.description),
        )
        txn = cur.fetchone()
        conn.commit()
        log.info("Withdraw $%.2f ← account %d (balance now $%.2f)", body.amount, body.account_id, new_balance)

    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        log.error("withdraw error: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        conn.close()

    return {
        "transaction_id":  txn["id"],
        "reference_id":    str(txn["reference_id"]),
        "type":            txn["type"],
        "amount":          float(txn["amount"]),
        "balance_after":   float(txn["balance_after"]),
        "created_at":      txn["created_at"],
    }


@app.get("/transactions/{account_id}")
def transaction_history(
    account_id: int,
    limit:  int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    try:
        conn = get_conn()
        cur  = conn.cursor()

        # Ownership check
        cur.execute("SELECT user_id FROM accounts WHERE id = %s", (account_id,))
        acc = cur.fetchone()
        if not acc:
            raise HTTPException(status_code=404, detail="Account not found")
        if acc["user_id"] != user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        cur.execute(
            """
            SELECT id, type, amount, balance_after, description, reference_id, created_at
            FROM transactions
            WHERE account_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (account_id, limit, offset),
        )
        rows = cur.fetchall()

        cur.execute("SELECT COUNT(*) as total FROM transactions WHERE account_id = %s", (account_id,))
        total = cur.fetchone()["total"]

        cur.close()
        conn.close()
    except HTTPException:
        raise
    except Exception as exc:
        log.error("history error: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")

    return {
        "account_id": account_id,
        "total":      total,
        "limit":      limit,
        "offset":     offset,
        "transactions": [
            {
                "id":           r["id"],
                "type":         r["type"],
                "amount":       float(r["amount"]),
                "balance_after": float(r["balance_after"]),
                "description":  r["description"],
                "reference_id": str(r["reference_id"]),
                "created_at":   r["created_at"],
            }
            for r in rows
        ],
    }
