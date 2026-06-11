# """
# account-service — FastAPI
# Endpoints:
#   GET    /accounts/health          liveness probe
#   GET    /accounts/profile         user profile
#   GET    /accounts/me              list user accounts
#   POST   /accounts                 open account
#   DELETE /accounts/{account_id}    close account
# """

# import os
# import sys
# import logging
# import random
# import string

# import psycopg2
# import psycopg2.extras
# from fastapi import FastAPI, HTTPException, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# import jwt
# from pydantic import BaseModel

# # ── Metrics (NEW) ─────────────────────────────────────────────────────────────
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# from common.metrics import (
#     setup_metrics,
#     ACCOUNTS_OPENED,
#     ACCOUNTS_CLOSED,
#     PROFILE_FETCHES,
# )

# logging.basicConfig(level=logging.INFO)
# log = logging.getLogger("account-service")

# DB_HOST = os.getenv("DB_HOST")
# DB_PORT = os.getenv("DB_PORT")
# DB_NAME = os.getenv("DB_NAME")
# DB_USER = os.getenv("DB_USER")
# DB_PASSWORD = os.getenv("DB_PASSWORD")
# JWT_SECRET = os.getenv("JWT_SECRET")
# JWT_ALGO = "HS256"

# app = FastAPI(title="BankApp · Account Service", version="1.0.0")
# app.add_middleware(
#     CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
# )

# # ── Prometheus setup (NEW) ────────────────────────────────────────────────────
# setup_metrics(app, service_name="account-service")

# security = HTTPBearer()


# def get_conn():
#     return psycopg2.connect(
#         host=DB_HOST,
#         port=DB_PORT,
#         dbname=DB_NAME,
#         user=DB_USER,
#         password=DB_PASSWORD,
#         cursor_factory=psycopg2.extras.RealDictCursor,
#     )


# def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(security),
# ) -> dict:
#     try:
#         payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
#         return {"user_id": int(payload["sub"]), "username": payload["username"]}
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token expired")
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")


# def generate_account_number() -> str:
#     return "".join(random.choices(string.digits, k=12))


# class OpenAccountRequest(BaseModel):
#     account_type: str = "checking"


# @app.get("/accounts/health")
# def health():
#     return {"status": "ok", "service": "account-service"}


# @app.get("/accounts/profile")
# def get_profile(user=Depends(get_current_user)):
#     try:
#         conn = get_conn()
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT id, username, email, full_name, created_at FROM users WHERE id = %s",
#             (user["user_id"],),
#         )
#         profile = cur.fetchone()
#         cur.close()
#         conn.close()
#     except Exception as exc:
#         log.error("profile error: %s", exc)
#         PROFILE_FETCHES.labels(status="db_error").inc()  # NEW
#         raise HTTPException(status_code=500, detail="Database error")

#     if not profile:
#         PROFILE_FETCHES.labels(status="not_found").inc()  # NEW
#         raise HTTPException(status_code=404, detail="User not found")

#     PROFILE_FETCHES.labels(status="success").inc()  # NEW
#     return dict(profile)


# @app.get("/accounts/me")
# def list_accounts(user=Depends(get_current_user)):
#     try:
#         conn = get_conn()
#         cur = conn.cursor()
#         cur.execute(
#             """
#             SELECT id, account_number, account_type, balance, is_active, created_at
#             FROM accounts WHERE user_id = %s ORDER BY created_at DESC
#             """,
#             (user["user_id"],),
#         )
#         accounts = cur.fetchall()
#         cur.close()
#         conn.close()
#     except Exception as exc:
#         log.error("list_accounts error: %s", exc)
#         raise HTTPException(status_code=500, detail="Database error")

#     return [dict(a) for a in accounts]


# @app.post("/accounts", status_code=201)
# def open_account(body: OpenAccountRequest, user=Depends(get_current_user)):
#     if body.account_type not in ("checking", "savings"):
#         raise HTTPException(
#             status_code=422, detail="account_type must be 'checking' or 'savings'"
#         )

#     acc_number = generate_account_number()
#     try:
#         conn = get_conn()
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO accounts (user_id, account_number, account_type, balance)
#             VALUES (%s, %s, %s, 0.00)
#             RETURNING id, account_number, account_type, balance, created_at
#             """,
#             (user["user_id"], acc_number, body.account_type),
#         )
#         account = cur.fetchone()
#         conn.commit()
#         cur.close()
#         conn.close()
#     except Exception as exc:
#         log.error("open_account error: %s", exc)
#         ACCOUNTS_OPENED.labels(
#             status="failure", account_type=body.account_type
#         ).inc()  # NEW
#         raise HTTPException(status_code=500, detail="Database error")

#     ACCOUNTS_OPENED.labels(
#         status="success", account_type=body.account_type
#     ).inc()  # NEW
#     return dict(account)


# @app.delete("/accounts/{account_id}")
# def close_account(account_id: int, user=Depends(get_current_user)):
#     conn = None
#     try:
#         conn = get_conn()
#         conn.autocommit = False
#         cur = conn.cursor()

#         cur.execute(
#             "SELECT id, user_id, balance, is_active FROM accounts WHERE id = %s FOR UPDATE",
#             (account_id,),
#         )
#         account = cur.fetchone()

#         if not account:
#             ACCOUNTS_CLOSED.labels(status="not_found").inc()  # NEW
#             raise HTTPException(status_code=404, detail="Account not found")
#         if account["user_id"] != user["user_id"]:
#             ACCOUNTS_CLOSED.labels(status="denied").inc()  # NEW
#             raise HTTPException(status_code=403, detail="Access denied")
#         if not account["is_active"]:
#             ACCOUNTS_CLOSED.labels(status="already_closed").inc()  # NEW
#             raise HTTPException(status_code=409, detail="Account already closed")
#         if float(account["balance"]) != 0.00:
#             ACCOUNTS_CLOSED.labels(status="balance_nonzero").inc()  # NEW
#             raise HTTPException(
#                 status_code=422,
#                 detail=(
#                     "Balance must be $0.00 before closing."
#                     f"Current balance: ${float(account['balance']):.2f}."
#                     "Please withdraw remaining funds first.")
#             )

#         cur.execute(
#             "SELECT COUNT(*) as c FROM accounts WHERE user_id = %s AND is_active = TRUE",
#             (user["user_id"],),
#         )
#         if cur.fetchone()["c"] <= 1:
#             ACCOUNTS_CLOSED.labels(status="last_account").inc()  # NEW
#             raise HTTPException(
#                 status_code=422, detail="Cannot close your only active account"
#             )

#         cur.execute(
#             "UPDATE accounts SET is_active = FALSE WHERE id = %s", (account_id,)
#         )
#         conn.commit()
#         cur.close()
#         conn.close()

#     except HTTPException:
#         if conn:
#             conn.rollback()
#         raise
#     except Exception as exc:
#         if conn:
#             conn.rollback()
#         log.error("close_account error: %s", exc)
#         ACCOUNTS_CLOSED.labels(status="db_error").inc()  # NEW
#         raise HTTPException(status_code=500, detail="Database error")

#     ACCOUNTS_CLOSED.labels(status="success").inc()  # NEW
#     return {"message": "Account successfully closed", "account_id": account_id}


"""
account-service — FastAPI
Endpoints:
  GET    /accounts/health          liveness probe
  GET    /accounts/profile         user profile
  GET    /accounts/me              list user accounts
  POST   /accounts                 open account
  DELETE /accounts/{account_id}    close account
"""

import logging
import os
import random
import string

import psycopg2
import psycopg2.extras
from common.metrics import (
    ACCOUNTS_CLOSED,
    ACCOUNTS_OPENED,
    PROFILE_FETCHES,
    setup_metrics,
)
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("account-service")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"

app = FastAPI(title="BankApp · Account Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# ── Prometheus setup (NEW) ────────────────────────────────────────────────────
setup_metrics(app, service_name="account-service")

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


def generate_account_number() -> str:
    return "".join(random.choices(string.digits, k=12))


class OpenAccountRequest(BaseModel):
    account_type: str = "checking"


@app.get("/accounts/health")
def health():
    return {"status": "ok", "service": "account-service"}


@app.get("/accounts/profile")
def get_profile(user=Depends(get_current_user)):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email, full_name, created_at FROM users WHERE id = %s",
            (user["user_id"],),
        )
        profile = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as exc:
        log.error("profile error: %s", exc)
        PROFILE_FETCHES.labels(status="db_error").inc()  # NEW
        raise HTTPException(status_code=500, detail="Database error")

    if not profile:
        PROFILE_FETCHES.labels(status="not_found").inc()  # NEW
        raise HTTPException(status_code=404, detail="User not found")

    PROFILE_FETCHES.labels(status="success").inc()  # NEW
    return dict(profile)


@app.get("/accounts/me")
def list_accounts(user=Depends(get_current_user)):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, account_number, account_type, balance, is_active, created_at
            FROM accounts WHERE user_id = %s ORDER BY created_at DESC
            """,
            (user["user_id"],),
        )
        accounts = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as exc:
        log.error("list_accounts error: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")

    return [dict(a) for a in accounts]


@app.post("/accounts", status_code=201)
def open_account(body: OpenAccountRequest, user=Depends(get_current_user)):
    if body.account_type not in ("checking", "savings"):
        raise HTTPException(
            status_code=422, detail="account_type must be 'checking' or 'savings'"
        )

    acc_number = generate_account_number()
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO accounts (user_id, account_number, account_type, balance)
            VALUES (%s, %s, %s, 0.00)
            RETURNING id, account_number, account_type, balance, created_at
            """,
            (user["user_id"], acc_number, body.account_type),
        )
        account = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        log.error("open_account error: %s", exc)
        ACCOUNTS_OPENED.labels(
            status="failure", account_type=body.account_type
        ).inc()  # NEW
        raise HTTPException(status_code=500, detail="Database error")

    ACCOUNTS_OPENED.labels(
        status="success", account_type=body.account_type
    ).inc()  # NEW
    return dict(account)


@app.delete("/accounts/{account_id}")
def close_account(account_id: int, user=Depends(get_current_user)):
    conn = None
    try:
        conn = get_conn()
        conn.autocommit = False
        cur = conn.cursor()

        cur.execute(
            "SELECT id, user_id, balance, is_active FROM accounts WHERE id = %s FOR UPDATE",
            (account_id,),
        )
        account = cur.fetchone()

        if not account:
            ACCOUNTS_CLOSED.labels(status="not_found").inc()  # NEW
            raise HTTPException(status_code=404, detail="Account not found")
        if account["user_id"] != user["user_id"]:
            ACCOUNTS_CLOSED.labels(status="denied").inc()  # NEW
            raise HTTPException(status_code=403, detail="Access denied")
        if not account["is_active"]:
            ACCOUNTS_CLOSED.labels(status="already_closed").inc()  # NEW
            raise HTTPException(status_code=409, detail="Account already closed")
        if float(account["balance"]) != 0.00:
            ACCOUNTS_CLOSED.labels(status="balance_nonzero").inc()  # NEW
            raise HTTPException(
                status_code=422,
                detail=(
                    "Balance must be $0.00 before closing."
                    f"Current balance: ${float(account['balance']):.2f}."
                    "Please withdraw remaining funds first.")
            )

        cur.execute(
            "SELECT COUNT(*) AS active_count FROM accounts WHERE user_id = %s AND is_active = TRUE",
            (user["user_id"],),
        )
        if cur.fetchone()["c"] <= 1:
            ACCOUNTS_CLOSED.labels(status="last_account").inc()  # NEW
            raise HTTPException(
                status_code=422, detail="Cannot close your only active account"
            )

        cur.execute(
            "UPDATE accounts SET is_active = FALSE WHERE id = %s", (account_id,)
        )
        conn.commit()
        cur.close()
        conn.close()

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        log.error("close_account error: %s", exc)
        ACCOUNTS_CLOSED.labels(status="db_error").inc()  # NEW
        raise HTTPException(status_code=500, detail="Database error")

    ACCOUNTS_CLOSED.labels(status="success").inc()  # NEW
    return {"message": "Account successfully closed", "account_id": account_id}
