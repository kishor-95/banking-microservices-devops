"""
auth-service  —  FastAPI
Responsibilities:
  POST /auth/register  → create user, return JWT
  POST /auth/login     → validate credentials, return JWT
  GET  /auth/verify    → validate JWT (called by sibling services)
  GET  /auth/health    → liveness probe for K8s
"""

import os
import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator

# ── Metrics ───────────────────────────────────────────────────────────────────
import time
from metrics import (
    REQUEST_COUNT, REQUEST_LATENCY, REQUESTS_IN_PROGRESS,
    record_login, record_registration, record_token_operation,
    metrics_endpoint
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("auth-service")

# ── Config (injected via env / K8s ConfigMap + Secret) ───────────────────────
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="BankApp · Auth Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production via env
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)  # allow None for /auth/verify, /auth/health

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


# ── DB helpers ────────────────────────────────────────────────────────────────


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


# ── JWT helpers ───────────────────────────────────────────────────────────────
def create_jwt(user_id: int, username: str) -> str:
    payload = {
        "sub":      str(user_id),
        "username": username,
        "iat":      datetime.now(timezone.utc),
        "exp":      datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Pydantic models ───────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username:  str
    email:     EmailStr
    password:  str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
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
    token_type:   str = "bearer"
    user_id:      int
    username:     str


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
        record_registration('duplicate')
        raise HTTPException(
            status_code=409, detail="Username or email already exists")
    except Exception as exc:
        log.error("register error: %s", exc)
        record_registration('failure')
        raise HTTPException(status_code=500, detail="Database error")

    token = create_jwt(row["id"], row["username"])
    record_registration('success')
    record_token_operation('create', 'success')
    log.info("New user registered: %s", row["username"])
    return TokenResponse(access_token=token, user_id=row["id"], username=row["username"])


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
        raise HTTPException(status_code=500, detail="Database error")

    if not user:
        record_login('invalid_credentials')
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user["is_active"]:
        record_login('account_disabled')
        raise HTTPException(status_code=403, detail="Account disabled")
    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        record_login('invalid_credentials')
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt(user["id"], user["username"])
    record_login('success')
    record_token_operation('create', 'success')
    log.info("User logged in: %s", user["username"])
    return TokenResponse(access_token=token, user_id=user["id"], username=user["username"])


@app.get("/auth/verify")
def verify(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials is None:
        raise HTTPException(status_code=403, detail="Not authenticated")
    payload = decode_jwt(credentials.credentials)
