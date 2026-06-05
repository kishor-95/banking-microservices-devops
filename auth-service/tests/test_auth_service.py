"""
test_auth_service.py — complete test suite for auth-service

Endpoints covered:
  GET  /auth/health    — no auth required
  POST /auth/register  — mock DB + mock bcrypt (bcrypt.gensalt is slow by design)
  POST /auth/login     — mock DB + mock bcrypt.checkpw
  GET  /auth/verify    — real JWT signed with TEST_JWT_SECRET

Mock strategy:
  - main.get_conn      → MagicMock psycopg2 connection (no real DB)
  - main.bcrypt.hashpw / gensalt / checkpw → patched (bcrypt is intentionally slow)
  - JWT secret         → set via os.environ in conftest.py before import

Run:
  cd auth-service
  pytest tests/ -v --cov=. --cov-report=term-missing
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import psycopg2.errors
from fastapi.testclient import TestClient

from main import app  # conftest.py ensures env vars are set before this import

# ── Constants ─────────────────────────────────────────────────────────────────
# Must match os.environ["JWT_SECRET"] set in conftest.py
TEST_JWT_SECRET = "test-secret-key-for-ci-only"

client = TestClient(app, raise_server_exceptions=False)


# ── Helpers ───────────────────────────────────────────────────────────────────
def make_token(user_id: int = 1, username: str = "testuser", expired: bool = False) -> str:
    """Generate a real JWT signed with the test secret."""
    delta = timedelta(hours=-1) if expired else timedelta(hours=1)
    payload = {
        "sub":      str(user_id),
        "username": username,
        "iat":      datetime.now(timezone.utc),
        "exp":      datetime.now(timezone.utc) + delta,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


def make_mock_conn(fetchone_result=None, fetchall_result=None):
    """Return a (conn, cur) MagicMock pair wired together."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.return_value = fetchone_result
    cur.fetchall.return_value = fetchall_result or []
    return conn, cur


# ══════════════════════════════════════════════════════════════════════════════
# GET /auth/health
# ══════════════════════════════════════════════════════════════════════════════
class TestHealth:
    def test_health_ok(self):
        """Liveness probe returns 200 with expected body — no deps needed."""
        resp = client.get("/auth/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "auth-service"


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/register
# ══════════════════════════════════════════════════════════════════════════════
class TestRegister:
    VALID_PAYLOAD = {
        "username":  "kishor95",
        "email":     "kishor@example.com",
        "password":  "securepass123",
        "full_name": "Kishor B",
    }

    @patch("main.bcrypt.gensalt", return_value=b"$2b$12$fakesalt")
    @patch("main.bcrypt.hashpw",  return_value=b"$2b$12$fakehash")
    @patch("main.get_conn")
    def test_register_success_returns_201_and_token(
        self, mock_get_conn, mock_hashpw, mock_gensalt
    ):
        """Happy path: DB inserts user, service returns 201 + JWT."""
        conn, cur = make_mock_conn(
            fetchone_result={"id": 42, "username": "kishor95"})
        mock_get_conn.return_value = conn

        resp = client.post("/auth/register", json=self.VALID_PAYLOAD)

        assert resp.status_code == 201
        body = resp.json()
        assert body["user_id"] == 42
        assert body["username"] == "kishor95"
        assert body["token_type"] == "bearer"
        assert "access_token" in body
        assert len(body["access_token"]) > 20  # real JWT, not empty string

    @patch("main.bcrypt.gensalt", return_value=b"$2b$12$fakesalt")
    @patch("main.bcrypt.hashpw",  return_value=b"$2b$12$fakehash")
    @patch("main.get_conn")
    def test_register_duplicate_returns_409(
        self, mock_get_conn, mock_hashpw, mock_gensalt
    ):
        """DB raises UniqueViolation → service returns 409 Conflict."""
        conn, cur = make_mock_conn()
        cur.execute.side_effect = psycopg2.errors.UniqueViolation
        mock_get_conn.return_value = conn

        resp = client.post("/auth/register", json=self.VALID_PAYLOAD)

        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_register_password_too_short_returns_422(self):
        """Pydantic validator rejects passwords shorter than 8 chars."""
        payload = {**self.VALID_PAYLOAD, "password": "short"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_username_too_short_returns_422(self):
        """Pydantic validator rejects usernames shorter than 3 chars."""
        payload = {**self.VALID_PAYLOAD, "username": "ab"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_invalid_email_returns_422(self):
        """Pydantic EmailStr rejects malformed email addresses."""
        payload = {**self.VALID_PAYLOAD, "email": "not-an-email"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_missing_required_fields_returns_422(self):
        """Missing username/email/password → 422 Unprocessable Entity."""
        resp = client.post("/auth/register", json={"username": "kishor95"})
        assert resp.status_code == 422

    @patch("main.bcrypt.gensalt", return_value=b"$2b$12$fakesalt")
    @patch("main.bcrypt.hashpw",  return_value=b"$2b$12$fakehash")
    @patch("main.get_conn")
    def test_register_db_error_returns_500(
        self, mock_get_conn, mock_hashpw, mock_gensalt
    ):
        """Generic DB exception → 500 with 'Database error' detail."""
        conn, cur = make_mock_conn()
        cur.execute.side_effect = Exception("connection timeout")
        mock_get_conn.return_value = conn

        resp = client.post("/auth/register", json=self.VALID_PAYLOAD)

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Database error"


# ══════════════════════════════════════════════════════════════════════════════
# POST /auth/login
# ══════════════════════════════════════════════════════════════════════════════
class TestLogin:
    VALID_PAYLOAD = {"username": "kishor95", "password": "securepass123"}

    def _active_user_row(self, is_active: bool = True) -> dict:
        return {
            "id":            1,
            "username":      "kishor95",
            "password_hash": "$2b$12$fakehash",
            "is_active":     is_active,
        }

    @patch("main.bcrypt.checkpw", return_value=True)
    @patch("main.get_conn")
    def test_login_success_returns_200_and_token(self, mock_get_conn, mock_checkpw):
        """Valid credentials → 200 + JWT TokenResponse."""
        conn, cur = make_mock_conn(fetchone_result=self._active_user_row())
        mock_get_conn.return_value = conn

        resp = client.post("/auth/login", json=self.VALID_PAYLOAD)

        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "kishor95"
        assert body["token_type"] == "bearer"
        assert "access_token" in body

    @patch("main.bcrypt.checkpw", return_value=False)
    @patch("main.get_conn")
    def test_login_wrong_password_returns_401(self, mock_get_conn, mock_checkpw):
        """Wrong password: bcrypt.checkpw returns False → 401."""
        conn, cur = make_mock_conn(fetchone_result=self._active_user_row())
        mock_get_conn.return_value = conn

        resp = client.post("/auth/login", json=self.VALID_PAYLOAD)

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    @patch("main.get_conn")
    def test_login_unknown_user_returns_401(self, mock_get_conn):
        """Username not in DB → fetchone returns None → 401."""
        conn, cur = make_mock_conn(fetchone_result=None)
        mock_get_conn.return_value = conn

        resp = client.post(
            "/auth/login", json={"username": "nobody", "password": "pass1234"})

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    @patch("main.get_conn")
    def test_login_disabled_account_returns_403(self, mock_get_conn):
        """is_active=False → 403 Account disabled (checked before bcrypt)."""
        conn, cur = make_mock_conn(
            fetchone_result=self._active_user_row(is_active=False))
        mock_get_conn.return_value = conn

        resp = client.post("/auth/login", json=self.VALID_PAYLOAD)

        assert resp.status_code == 403
        assert "disabled" in resp.json()["detail"]

    def test_login_empty_body_returns_422(self):
        """No body at all → 422 Unprocessable Entity."""
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 422

    @patch("main.get_conn")
    def test_login_db_error_returns_500(self, mock_get_conn):
        """DB connection failure → 500."""
        conn, cur = make_mock_conn()
        cur.execute.side_effect = Exception("DB unreachable")
        mock_get_conn.return_value = conn

        resp = client.post("/auth/login", json=self.VALID_PAYLOAD)

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Database error"


# ══════════════════════════════════════════════════════════════════════════════
# GET /auth/verify
# ══════════════════════════════════════════════════════════════════════════════
class TestVerify:
    """
    /auth/verify uses HTTPBearer + decode_jwt (no dependency_override needed).
    Tests pass real JWTs signed with TEST_JWT_SECRET.
    """

    def test_verify_valid_token_returns_claims(self):
        """Valid Bearer token → 200 with decoded user claims."""
        token = make_token(user_id=7, username="kishor95")
        resp = client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["user_id"] == "7"
        assert body["username"] == "kishor95"

    def test_verify_garbage_token_returns_401(self):
        """Malformed token string → 401 Invalid token."""
        resp = client.get(
            "/auth/verify",
            headers={"Authorization": "Bearer this.is.garbage"}
        )
        assert resp.status_code == 401

    def test_verify_expired_token_returns_401(self):
        """Expired token → 401 Token expired."""
        expired_token = make_token(expired=True)
        resp = client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_verify_no_auth_header_returns_401(self):
        """No Authorization header → 401 (HTTPBearer requirement)."""
        resp = client.get("/auth/verify")
        assert resp.status_code == 401

    def test_verify_wrong_secret_returns_401(self):
        """Token signed with wrong secret → 401 Invalid token."""
        bad_token = jwt.encode(
            {"sub": "1", "username": "hacker",
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret",
            algorithm="HS256",
        )
        resp = client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {bad_token}"}
        )
        assert resp.status_code == 401
