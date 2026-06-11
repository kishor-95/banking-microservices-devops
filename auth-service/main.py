"""
auth-service — FastAPI
Endpoints:
  GET  /auth/health    liveness probe
  POST /auth/register  create user, return JWT
  POST /auth/login     validate credentials, return JWT
  GET  /auth/verify    validate JWT (called by sibling services)
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator

# ── Metrics (NEW) ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.metrics import (
    setup_metrics,
    AUTH_REGISTRATIONS,
    AUTH_LOGINS,
    AUTH_TOKEN_VERIFICATIONS,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("auth-service")

# ── Config ────────────────────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="BankApp · Auth Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# ── Prometheus setup (NEW) ────────────────────────────────────────────────────
setup_metrics(app, service_name="auth-service")

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


def create_jwt(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Models ────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_clean(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/auth/health")
def health():
    return {"status": "ok", "service": "auth-service"}


@app.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest):
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, full_name)
            VALUES (%s, %s, %s, %s)
            RETURNING id, username
            """,
            (body.username, body.email, hashed, body.full_name),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
    except psycopg2.errors.UniqueViolation:
        AUTH_REGISTRATIONS.labels(status="failure").inc()  # NEW
        raise HTTPException(status_code=409, detail="Username or email already exists")
    except Exception as exc:
        log.error("register error: %s", exc)
        AUTH_REGISTRATIONS.labels(status="failure").inc()  # NEW
        raise HTTPException(status_code=500, detail="Database error")

    token = create_jwt(row["id"], row["username"])
    AUTH_REGISTRATIONS.labels(status="success").inc()  # NEW
    return TokenResponse(
        access_token=token, user_id=row["id"], username=row["username"]
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password_hash, is_active FROM users WHERE username = %s",
            (body.username.strip().lower(),),
        )
        user = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as exc:
        log.error("login db error: %s", exc)
        AUTH_LOGINS.labels(status="db_error").inc()  # NEW
        raise HTTPException(status_code=500, detail="Database error")

    if not user:
        AUTH_LOGINS.labels(status="invalid_credentials").inc()  # NEW
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user["is_active"]:
        AUTH_LOGINS.labels(status="disabled").inc()  # NEW
        raise HTTPException(status_code=403, detail="Account disabled")
    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        AUTH_LOGINS.labels(status="invalid_credentials").inc()  # NEW
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt(user["id"], user["username"])
    AUTH_LOGINS.labels(status="success").inc()  # NEW
    return TokenResponse(
        access_token=token, user_id=user["id"], username=user["username"]
    )


@app.get("/auth/verify")
def verify(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = decode_jwt(credentials.credentials)
    except HTTPException as exc:
        label = "expired" if "expired" in exc.detail.lower() else "invalid"
        AUTH_TOKEN_VERIFICATIONS.labels(status=label).inc()  # NEW
        raise

    AUTH_TOKEN_VERIFICATIONS.labels(status="success").inc()  # NEW
    return {"valid": True, "user_id": payload["sub"], "username": payload["username"]}
