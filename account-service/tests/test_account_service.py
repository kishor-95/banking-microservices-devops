"""
test_account_service.py — complete test suite for account-service

Endpoints covered:
  GET    /accounts/health          — no auth
  GET    /accounts/profile         — auth required
  GET    /accounts/me              — auth required
  POST   /accounts                 — auth required
  DELETE /accounts/{account_id}    — auth required + business rules

Mock strategy:
  - app.dependency_overrides[get_current_user] → bypass JWT entirely
  - main.get_conn → MagicMock psycopg2 connection (no real DB)

Run:
  cd account-service
  pytest tests/ -v --cov=. --cov-report=term-missing
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app, get_current_user

# ── Fake authenticated user ───────────────────────────────────────────────────
FAKE_USER = {"user_id": 1, "username": "testuser"}
FAKE_USER_ALT = {"user_id": 2, "username": "otheruser"}

client = TestClient(app, raise_server_exceptions=False)


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def inject_fake_auth():
    """Override JWT dependency — every test gets FAKE_USER by default."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield
    app.dependency_overrides.clear()


def make_mock_conn(fetchone=None, fetchall=None, fetchone_side_effect=None):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    if fetchone_side_effect:
        cur.fetchone.side_effect = fetchone_side_effect
    else:
        cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall or []
    return conn, cur


def make_account_row(**overrides) -> dict:
    base = {
        "id":             1,
        "account_number": "123456789012",
        "account_type":   "checking",
        "balance":        500.00,
        "is_active":      True,
        "created_at":     datetime(2024, 1, 1),
    }
    return {**base, **overrides}


# ══════════════════════════════════════════════════════════════════════════════
# GET /accounts/health
# ══════════════════════════════════════════════════════════════════════════════
class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/accounts/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["service"] == "account-service"


# ══════════════════════════════════════════════════════════════════════════════
# GET /accounts/profile
# ══════════════════════════════════════════════════════════════════════════════
class TestGetProfile:
    PROFILE_ROW = {
        "id":         1,
        "username":   "testuser",
        "email":      "test@example.com",
        "full_name":  "Test User",
        "created_at": datetime(2024, 1, 1),
    }

    @patch("main.get_conn")
    def test_profile_success_returns_user_data(self, mock_get_conn):
        """200 + profile dict when user exists."""
        conn, cur = make_mock_conn(fetchone=self.PROFILE_ROW)
        mock_get_conn.return_value = conn

        resp = client.get("/accounts/profile")

        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "testuser"
        assert body["email"] == "test@example.com"
        assert body["full_name"] == "Test User"

    @patch("main.get_conn")
    def test_profile_user_not_found_returns_404(self, mock_get_conn):
        """fetchone returns None → 404 User not found."""
        conn, cur = make_mock_conn(fetchone=None)
        mock_get_conn.return_value = conn

        resp = client.get("/accounts/profile")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("main.get_conn")
    def test_profile_db_error_returns_500(self, mock_get_conn):
        """DB exception → 500."""
        conn, cur = make_mock_conn()
        cur.execute.side_effect = Exception("DB gone")
        mock_get_conn.return_value = conn

        resp = client.get("/accounts/profile")
        assert resp.status_code == 500

    def test_profile_no_auth_returns_401(self):
        """No Authorization header → 401 (FastAPI HTTPBearer default)."""
        app.dependency_overrides.clear()
        resp = client.get("/accounts/profile")
        assert resp.status_code == 401
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER


# ══════════════════════════════════════════════════════════════════════════════
# GET /accounts/me
# ══════════════════════════════════════════════════════════════════════════════
class TestListAccounts:
    @patch("main.get_conn")
    def test_list_accounts_returns_all_user_accounts(self, mock_get_conn):
        """200 + list of accounts for authenticated user."""
        rows = [
            make_account_row(id=1, account_type="checking"),
            make_account_row(id=2, account_type="savings"),
        ]
        conn, cur = make_mock_conn(fetchall=rows)
        mock_get_conn.return_value = conn

        resp = client.get("/accounts/me")

        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2
        assert body[0]["account_type"] == "checking"
        assert body[1]["account_type"] == "savings"

    @patch("main.get_conn")
    def test_list_accounts_empty_returns_empty_list(self, mock_get_conn):
        """User with no accounts → 200 with []."""
        conn, cur = make_mock_conn(fetchall=[])
        mock_get_conn.return_value = conn

        resp = client.get("/accounts/me")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch("main.get_conn")
    def test_list_accounts_db_error_returns_500(self, mock_get_conn):
        conn, cur = make_mock_conn()
        cur.execute.side_effect = Exception("timeout")
        mock_get_conn.return_value = conn

        resp = client.get("/accounts/me")
        assert resp.status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# POST /accounts
# ══════════════════════════════════════════════════════════════════════════════
class TestOpenAccount:
    @patch("main.get_conn")
    def test_open_checking_account_returns_201(self, mock_get_conn):
        """Valid account_type='checking' → 201 + account row."""
        row = make_account_row(account_type="checking", balance=0.00)
        conn, cur = make_mock_conn(fetchone=row)
        mock_get_conn.return_value = conn

        resp = client.post("/accounts", json={"account_type": "checking"})

        assert resp.status_code == 201
        body = resp.json()
        assert body["account_type"] == "checking"
        assert body["balance"] == 0.0

    @patch("main.get_conn")
    def test_open_savings_account_returns_201(self, mock_get_conn):
        """Valid account_type='savings' → 201."""
        row = make_account_row(account_type="savings", balance=0.00)
        conn, cur = make_mock_conn(fetchone=row)
        mock_get_conn.return_value = conn

        resp = client.post("/accounts", json={"account_type": "savings"})

        assert resp.status_code == 201
        assert resp.json()["account_type"] == "savings"

    @patch("main.get_conn")
    def test_open_invalid_account_type_returns_422(self, mock_get_conn):
        """account_type not in ('checking','savings') → 422 from endpoint guard."""
        resp = client.post("/accounts", json={"account_type": "crypto"})
        assert resp.status_code == 422
        assert "account_type" in resp.json()["detail"]

    @patch("main.get_conn")
    def test_open_account_default_type_is_checking(self, mock_get_conn):
        """Body omitted → defaults to 'checking'."""
        row = make_account_row(account_type="checking", balance=0.00)
        conn, cur = make_mock_conn(fetchone=row)
        mock_get_conn.return_value = conn

        resp = client.post("/accounts", json={})
        assert resp.status_code == 201

    @patch("main.get_conn")
    def test_open_account_db_error_returns_500(self, mock_get_conn):
        conn, cur = make_mock_conn()
        cur.execute.side_effect = Exception("DB error")
        mock_get_conn.return_value = conn

        resp = client.post("/accounts", json={"account_type": "checking"})
        assert resp.status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /accounts/{account_id}
# ══════════════════════════════════════════════════════════════════════════════
class TestCloseAccount:
    """
    Business rules under test:
      1. Account must exist
      2. Must be owner
      3. Must be active
      4. Balance must be $0.00
      5. Must have >= 2 active accounts (can't close the last one)
    """

    @patch("main.get_conn")
    def test_close_account_success(self, mock_get_conn):
        """Happy path: zero balance, owner, 2 active accounts → 200."""
        conn, cur = make_mock_conn(
            fetchone_side_effect=[
                {"id": 1, "user_id": 1, "balance": 0.00, "is_active": True},
                {"active_count": 2},
            ]
        )
        mock_get_conn.return_value = conn

        resp = client.delete("/accounts/1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["account_id"] == 1
        assert "closed" in body["message"].lower()

    @patch("main.get_conn")
    def test_close_account_not_found_returns_404(self, mock_get_conn):
        """Account ID doesn't exist → fetchone returns None → 404."""
        conn, cur = make_mock_conn(fetchone=None)
        mock_get_conn.return_value = conn

        resp = client.delete("/accounts/999")
        assert resp.status_code == 404

    @patch("main.get_conn")
    def test_close_account_wrong_owner_returns_403(self, mock_get_conn):
        """Account belongs to user_id=99, authenticated as user_id=1 → 403."""
        conn, cur = make_mock_conn(
            fetchone={"id": 5, "user_id": 99,
                      "balance": 0.00, "is_active": True}
        )
        mock_get_conn.return_value = conn

        resp = client.delete("/accounts/5")
        assert resp.status_code == 403
        assert "denied" in resp.json()["detail"].lower()

    @patch("main.get_conn")
    def test_close_already_closed_account_returns_409(self, mock_get_conn):
        """is_active=False → 409 Already closed."""
        conn, cur = make_mock_conn(
            fetchone={"id": 1, "user_id": 1,
                      "balance": 0.00, "is_active": False}
        )
        mock_get_conn.return_value = conn

        resp = client.delete("/accounts/1")
        assert resp.status_code == 409

    @patch("main.get_conn")
    def test_close_account_nonzero_balance_returns_422(self, mock_get_conn):
        """Balance=$150 → 422 (must withdraw first)."""
        conn, cur = make_mock_conn(
            fetchone={"id": 1, "user_id": 1,
                      "balance": 150.00, "is_active": True}
        )
        mock_get_conn.return_value = conn

        resp = client.delete("/accounts/1")
        assert resp.status_code == 422
        assert "$150.00" in resp.json()["detail"]

    @patch("main.get_conn")
    def test_close_only_active_account_returns_422(self, mock_get_conn):
        """Only 1 active account left → cannot close → 422."""
        conn, cur = make_mock_conn(
            fetchone_side_effect=[
                {"id": 1, "user_id": 1, "balance": 0.00, "is_active": True},
                {"active_count": 1},
            ]
        )
        mock_get_conn.return_value = conn

        resp = client.delete("/accounts/1")
        assert resp.status_code == 422
        assert "only active account" in resp.json()["detail"].lower()
