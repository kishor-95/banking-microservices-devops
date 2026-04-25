"""
test_balance_service.py — complete test suite for balance-service

Endpoints covered:
  GET /balance/health             — no auth
  GET /balance/{account_id}       — auth + ownership + active check
  GET /balance                    — auth, returns all user balances

Mock strategy:
  - app.dependency_overrides[get_current_user] → injects FAKE_USER
  - main.get_conn → MagicMock (no real DB)

Key business rules tested:
  - Ownership: account["username"] must match user["username"]
  - Active: is_active=False → 403
  - Not found: fetchone returns None → 404

Run:
  cd balance-service
  pytest tests/ -v --cov=. --cov-report=term-missing
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app, get_current_user

FAKE_USER = {"user_id": 1, "username": "testuser"}

client = TestClient(app, raise_server_exceptions=False)


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def inject_fake_auth():
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield
    app.dependency_overrides.clear()


def make_mock_conn(fetchone=None, fetchall=None):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.return_value = fetchone
    cur.fetchall.return_value = fetchall or []
    return conn, cur


def make_account_row(**overrides) -> dict:
    """Full account row including joined user fields (for GET /balance/{id})."""
    base = {
        "id":             1,
        "account_number": "123456789012",
        "account_type":   "checking",
        "balance":        250.75,
        "is_active":      True,
        "created_at":     datetime(2024, 1, 1),
        "username":       "testuser",   # must match FAKE_USER["username"]
        "full_name":      "Test User",
    }
    return {**base, **overrides}


def make_balance_row(**overrides) -> dict:
    """Compact row for GET /balance (all accounts)."""
    base = {
        "id":             1,
        "account_number": "123456789012",
        "account_type":   "checking",
        "balance":        250.75,
        "is_active":      True,
        "created_at":     datetime(2024, 1, 1),
    }
    return {**base, **overrides}


# ══════════════════════════════════════════════════════════════════════════════
# GET /balance/health
# ══════════════════════════════════════════════════════════════════════════════
class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/balance/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["service"] == "balance-service"


# ══════════════════════════════════════════════════════════════════════════════
# GET /balance/{account_id}
# ══════════════════════════════════════════════════════════════════════════════
class TestGetBalance:
    @patch("main.get_conn")
    def test_get_balance_success(self, mock_get_conn):
        """200 + balance details for own active account."""
        conn, cur = make_mock_conn(fetchone=make_account_row())
        mock_get_conn.return_value = conn

        resp = client.get("/balance/1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["account_id"] == 1
        assert body["balance"] == 250.75
        assert body["account_type"] == "checking"
        assert body["account_number"] == "123456789012"
        assert body["owner"] == "Test User"

    @patch("main.get_conn")
    def test_get_balance_not_found_returns_404(self, mock_get_conn):
        """Account ID not in DB → fetchone returns None → 404."""
        conn, cur = make_mock_conn(fetchone=None)
        mock_get_conn.return_value = conn

        resp = client.get("/balance/999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("main.get_conn")
    def test_get_balance_wrong_owner_returns_403(self, mock_get_conn):
        """
        Account belongs to 'otheruser' — authenticated as 'testuser'.
        Service checks account['username'] != user['username'] → 403.
        """
        conn, cur = make_mock_conn(
            fetchone=make_account_row(username="otheruser")
        )
        mock_get_conn.return_value = conn

        resp = client.get("/balance/1")
        assert resp.status_code == 403
        assert "denied" in resp.json()["detail"].lower()

    @patch("main.get_conn")
    def test_get_balance_inactive_account_returns_403(self, mock_get_conn):
        """is_active=False → 403 Account is inactive."""
        conn, cur = make_mock_conn(
            fetchone=make_account_row(is_active=False)
        )
        mock_get_conn.return_value = conn

        resp = client.get("/balance/1")
        assert resp.status_code == 403
        assert "inactive" in resp.json()["detail"].lower()

    @patch("main.get_conn")
    def test_get_balance_uses_full_name_when_available(self, mock_get_conn):
        """owner field is full_name when present, falls back to username."""
        conn, cur = make_mock_conn(
            fetchone=make_account_row(full_name="Kishor Bhairat")
        )
        mock_get_conn.return_value = conn

        resp = client.get("/balance/1")
        assert resp.status_code == 200
        assert resp.json()["owner"] == "Kishor Bhairat"

    @patch("main.get_conn")
    def test_get_balance_falls_back_to_username_when_no_full_name(self, mock_get_conn):
        """owner = username when full_name is None."""
        conn, cur = make_mock_conn(
            fetchone=make_account_row(full_name=None)
        )
        mock_get_conn.return_value = conn

        resp = client.get("/balance/1")
        assert resp.status_code == 200
        assert resp.json()["owner"] == "testuser"

    @patch("main.get_conn")
    def test_get_balance_db_error_returns_500(self, mock_get_conn):
        conn, cur = make_mock_conn()
        cur.execute.side_effect = Exception("connection lost")
        mock_get_conn.return_value = conn

        resp = client.get("/balance/1")
        assert resp.status_code == 500

    def test_get_balance_no_auth_returns_403(self):
        """Without auth override, missing header → 403."""
        app.dependency_overrides.clear()
        resp = client.get("/balance/1")
        assert resp.status_code == 403
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER


# ══════════════════════════════════════════════════════════════════════════════
# GET /balance  (all accounts for user)
# ══════════════════════════════════════════════════════════════════════════════
class TestGetAllBalances:
    @patch("main.get_conn")
    def test_get_all_balances_returns_list(self, mock_get_conn):
        """200 + list of balances for authenticated user."""
        rows = [
            make_balance_row(id=1, account_type="checking", balance=250.75),
            make_balance_row(id=2, account_type="savings",  balance=1000.00),
        ]
        conn, cur = make_mock_conn(fetchall=rows)
        mock_get_conn.return_value = conn

        resp = client.get("/balance")

        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2
        assert body[0]["balance"] == 250.75
        assert body[0]["account_type"] == "checking"
        assert body[1]["balance"] == 1000.00
        assert body[1]["account_type"] == "savings"

    @patch("main.get_conn")
    def test_get_all_balances_no_accounts_returns_empty_list(self, mock_get_conn):
        """User has no active accounts → 200 with []."""
        conn, cur = make_mock_conn(fetchall=[])
        mock_get_conn.return_value = conn

        resp = client.get("/balance")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch("main.get_conn")
    def test_get_all_balances_response_shape(self, mock_get_conn):
        """Verify exact keys in each balance item."""
        rows = [make_balance_row()]
        conn, cur = make_mock_conn(fetchall=rows)
        mock_get_conn.return_value = conn

        resp = client.get("/balance")
        item = resp.json()[0]

        assert "account_id" in item
        assert "account_number" in item
        assert "account_type" in item
        assert "balance" in item

    @patch("main.get_conn")
    def test_get_all_balances_db_error_returns_500(self, mock_get_conn):
        conn, cur = make_mock_conn()
        cur.execute.side_effect = Exception("query failed")
        mock_get_conn.return_value = conn

        resp = client.get("/balance")
        assert resp.status_code == 500
