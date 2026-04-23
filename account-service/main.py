# """
# account-service  —  FastAPI
# Responsibilities:
#   POST /accounts           → open a new bank account for the authenticated user
#   GET  /accounts/me        → list all accounts for the authenticated user
#   GET  /accounts/profile   → return user profile info
#   GET  /accounts/health    → liveness probe
# """

# import os
# import logging
# import string
# import secrets


# import psycopg2
# import psycopg2.extras
# from fastapi import FastAPI, HTTPException, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# import jwt
# from pydantic import BaseModel

# # ── Logging ───────────────────────────────────────────────────────────────────
# logging.basicConfig(level=logging.INFO)
# log = logging.getLogger("account-service")
# DB_ERROR = "Database error"

# # ── Config ────────────────────────────────────────────────────────────────────
# DB_HOST = os.getenv("DB_HOST")
# DB_PORT = os.getenv("DB_PORT")
# DB_NAME = os.getenv("DB_NAME")
# DB_USER = os.getenv("DB_USER")
# DB_PASSWORD = os.getenv("DB_PASSWORD")
# JWT_SECRET = os.getenv("JWT_SECRET")
# JWT_ALGO = "HS256"
# # ── FastAPI ───────────────────────────────────────────────────────────────────
# app = FastAPI(title="BankApp · Account Service", version="1.0.0")
# app.add_middleware(CORSMiddleware, allow_origins=[
#                    "*"], allow_methods=["*"], allow_headers=["*"])
# security = HTTPBearer()

# # ── Helpers ───────────────────────────────────────────────────────────────────


# def get_conn():
#     return psycopg2.connect(
#         host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
#         user=DB_USER, password=DB_PASSWORD,
#         cursor_factory=psycopg2.extras.RealDictCursor,
#     )


# def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
#     """Validate JWT locally — no network hop to auth-service for hot paths."""
#     try:
#         payload = jwt.decode(credentials.credentials,
#                              JWT_SECRET, algorithms=[JWT_ALGO])
#         return {"user_id": int(payload["sub"]), "username": payload["username"]}
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token expired")
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")


# def generate_account_number() -> str:
#     """16-digit account number, formatted as 4 groups of 4."""
#     digits = "".join(secrets.choice(string.digits) for _ in range(12))
#     return digits


# # ── Pydantic models ───────────────────────────────────────────────────────────
# class OpenAccountRequest(BaseModel):
#     account_type: str = "checking"

#     class Config:
#         json_schema_extra = {"example": {"account_type": "savings"}}


# # ── Routes ────────────────────────────────────────────────────────────────────
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
#         log.error("profile fetch error: %s", exc)
#         raise HTTPException(status_code=500, detail=DB_ERROR)

#     if not profile:
#         raise HTTPException(status_code=404, detail="User not found")

#     return dict(profile)


# @app.get("/accounts/me")
# def list_accounts(user=Depends(get_current_user)):
#     try:
#         conn = get_conn()
#         cur = conn.cursor()
#         cur.execute(
#             """
#             SELECT id, account_number, account_type, balance, is_active, created_at
#             FROM accounts
#             WHERE user_id = %s
#             ORDER BY created_at DESC
#             """,
#             (user["user_id"],),
#         )
#         accounts = cur.fetchall()
#         cur.close()
#         conn.close()
#     except Exception as exc:
#         log.error("list_accounts error: %s", exc)
#         raise HTTPException(status_code=500, detail=DB_ERROR)

#     return [dict(a) for a in accounts]


# @app.post("/accounts", status_code=201)
# def open_account(body: OpenAccountRequest, user=Depends(get_current_user)):
#     if body.account_type not in ("checking", "savings"):
#         raise HTTPException(status_code=422,
#                             detail="account_type must be 'checking' or 'savings'")

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
#             (user["user_id"], acc_number, body.account_type)  # edited
#         ),
#         account = cur.fetchone()
#         conn.commit()
#         cur.close()
#         conn.close()
#     except Exception as exc:
#         log.error("open_account error: %s", exc)
#         raise HTTPException(status_code=500, detail=DB_ERROR)

#     log.info("Account opened: %s for user %s", acc_number, user["username"])
#     return dict(account)


# @app.delete("/accounts/{account_id}", status_code=200)
# def close_account(account_id: int, user=Depends(get_current_user)):
#     """
#     Soft-close an account. Rules:
#       1. Must be the owner
#       2. Balance must be $0.00 (withdraw first)
#       3. Must have at least one other active account remaining
#     """
#     try:
#         conn = get_conn()
#         conn.autocommit = False
#         cur = conn.cursor()

#         # Fetch the account with row lock
#         cur.execute(
#             "SELECT id, user_id, balance, is_active FROM accounts WHERE id = %s FOR UPDATE",
#             (account_id,),
#         )
#         account = cur.fetchone()

#         if not account:
#             raise HTTPException(status_code=404, detail="Account not found")
#         if account["user_id"] != user["user_id"]:
#             raise HTTPException(status_code=403, detail="Access denied")
#         if not account["is_active"]:
#             raise HTTPException(
#                 status_code=409, detail="Account is already closed")
#         if abs(float(account["balance"])) > 0.001:
#             raise HTTPException(
#                 status_code=422,
#                 detail=(
#                     "Balance must be $0.00 before closing."
#                     f"Current balance: ${float(account['balance']):.2f}."
#                     "Please withdraw remaining funds first.")
#             )

#         # Ensure user keeps at least one active account
#         cur.execute(
#             "SELECT COUNT(*) as active_count FROM accounts WHERE user_id = %s AND is_active = TRUE",
#             (user["user_id"],),
#         )
#         active_count = cur.fetchone()["active_count"]
#         if active_count <= 1:
#             raise HTTPException(
#                 status_code=422,
#                 detail="Cannot close your only active account. Open a new account first."
#             )

#         # Soft-close — preserve all history
#         cur.execute(
#             "UPDATE accounts SET is_active = FALSE, updated_at = NOW() WHERE id = %s",
#             (account_id,),
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
#         raise HTTPException(status_code=500, detail="Database error")

#     log.info("Account %d closed by user %s", account_id, user["username"])
#     return {"message": "Account successfully closed", "account_id": account_id}


## New Code 
"""account-service — FastAPI
Responsibilities:
  POST /accounts           → open a new bank account for the authenticated user
  GET  /accounts/me        → list all accounts for the authenticated user
  GET  /accounts/profile   → return user profile info
  GET  /accounts/health    → liveness probe
"""

from contextlib import closing
from decimal import Decimal
import logging
import os
import secrets
import string
from typing import Any, Dict, Optional

import jwt
import psycopg2
import psycopg2.extras
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("account-service")

# ── Config ────────────────────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"

# ── Constants ────────────────────────────────────────────────────────────────
DB_ERROR_DETAIL = "Database error"
TOKEN_EXPIRED_DETAIL = "Token expired"
INVALID_TOKEN_DETAIL = "Invalid token"
USER_NOT_FOUND_DETAIL = "User not found"
ACCESS_DENIED_DETAIL = "Access denied"
ACCOUNT_NOT_FOUND_DETAIL = "Account not found"
ACCOUNT_ALREADY_CLOSED_DETAIL = "Account is already closed"
ONLY_ACTIVE_ACCOUNT_DETAIL = "Cannot close your only active account. Open a new account first."
ACCOUNT_TYPE_VALIDATION_DETAIL = "account_type must be 'checking' or 'savings'"
ACCOUNT_TYPES = {"checking", "savings"}
ACCOUNT_NUMBER_LENGTH = 12
ZERO_BALANCE = Decimal("0.00")
BALANCE_TOLERANCE = Decimal("0.0001")

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="BankApp · Account Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer()


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _raise_db_error(action: str, exc: Exception) -> None:
    log.exception("%s error", action)
    raise HTTPException(status_code=500, detail=DB_ERROR_DETAIL) from exc


def _is_zero_balance(balance: Any) -> bool:
    """Compare balances safely without relying on float equality."""
    if balance is None:
        return True

    try:
        return abs(Decimal(str(balance)) - ZERO_BALANCE) <= BALANCE_TOLERANCE
    except (ArithmeticError, ValueError, TypeError):
        return False


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Validate JWT locally — no network hop to auth-service for hot paths."""
    try:
        if not JWT_SECRET:
            raise jwt.InvalidTokenError("JWT secret not configured")

        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        return {"user_id": int(payload["sub"]), "username": payload["username"]}
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail=TOKEN_EXPIRED_DETAIL) from exc
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL) from exc


def generate_account_number() -> str:
    """Generate a 12-digit account number."""
    return "".join(secrets.choice(string.digits) for _ in range(ACCOUNT_NUMBER_LENGTH))


# ── Pydantic models ───────────────────────────────────────────────────────────
class OpenAccountRequest(BaseModel):
    account_type: str = "checking"

    class Config:
        json_schema_extra = {"example": {"account_type": "savings"}}


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/accounts/health")
def health():
    return {"status": "ok", "service": "account-service"}


@app.get("/accounts/profile")
def get_profile(user=Depends(get_current_user)):
    try:
        with closing(get_conn()) as conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, username, email, full_name, created_at FROM users WHERE id = %s",
                        (user["user_id"],),
                    )
                    profile = cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        _raise_db_error("profile fetch", exc)

    if not profile:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND_DETAIL)

    return dict(profile)


@app.get("/accounts/me")
def list_accounts(user=Depends(get_current_user)):
    try:
        with closing(get_conn()) as conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, account_number, account_type, balance, is_active, created_at
                        FROM accounts
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        """,
                        (user["user_id"],),
                    )
                    accounts = cur.fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        _raise_db_error("list_accounts", exc)

    return [dict(account) for account in accounts]


@app.post("/accounts", status_code=201)
def open_account(body: OpenAccountRequest, user=Depends(get_current_user)):
    if body.account_type not in ACCOUNT_TYPES:
        raise HTTPException(status_code=422, detail=ACCOUNT_TYPE_VALIDATION_DETAIL)

    acc_number = generate_account_number()

    try:
        with closing(get_conn()) as conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO accounts (user_id, account_number, account_type, balance)
                        VALUES (%s, %s, %s, 0.00)
                        RETURNING id, account_number, account_type, balance, created_at
                        """,
                        (user["user_id"], acc_number, body.account_type),
                    )
                    account = cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        _raise_db_error("open_account", exc)

    log.info("Account opened: %s for user %s", acc_number, user["username"])
    return dict(account)


@app.delete("/accounts/{account_id}", status_code=200)
def close_account(account_id: int, user=Depends(get_current_user)):
    """
    Soft-close an account. Rules:
      1. Must be the owner
      2. Balance must be $0.00 (withdraw first)
      3. Must have at least one other active account remaining
    """
    try:
        with closing(get_conn()) as conn:
            with conn:
                with conn.cursor() as cur:
                    # Fetch the account with row lock
                    cur.execute(
                        "SELECT id, user_id, balance, is_active FROM accounts WHERE id = %s FOR UPDATE",
                        (account_id,),
                    )
                    account = cur.fetchone()

                    if not account:
                        raise HTTPException(status_code=404, detail=ACCOUNT_NOT_FOUND_DETAIL)
                    if account["user_id"] != user["user_id"]:
                        raise HTTPException(status_code=403, detail=ACCESS_DENIED_DETAIL)
                    if not account["is_active"]:
                        raise HTTPException(status_code=409, detail=ACCOUNT_ALREADY_CLOSED_DETAIL)
                    if not _is_zero_balance(account["balance"]):
                        balance_value = Decimal(str(account["balance"]))
                        raise HTTPException(
                            status_code=422,
                            detail=(
                                f"Balance must be $0.00 before closing. Current balance: ${balance_value:.2f}. "
                                "Please withdraw remaining funds first."
                            ),
                        )

                    # Ensure user keeps at least one active account
                    cur.execute(
                        "SELECT COUNT(*) as active_count FROM accounts WHERE user_id = %s AND is_active = TRUE",
                        (user["user_id"],),
                    )
                    active_row = cur.fetchone() or {"active_count": 0}
                    active_count = active_row["active_count"]
                    if active_count <= 1:
                        raise HTTPException(
                            status_code=422,
                            detail=ONLY_ACTIVE_ACCOUNT_DETAIL,
                        )

                    # Soft-close — preserve all history
                    cur.execute(
                        "UPDATE accounts SET is_active = FALSE, updated_at = NOW() WHERE id = %s",
                        (account_id,),
                    )
    except HTTPException:
        raise
    except Exception as exc:
        _raise_db_error("close_account", exc)

    log.info("Account %d closed by user %s", account_id, user["username"])
    return {"message": "Account successfully closed", "account_id": account_id}