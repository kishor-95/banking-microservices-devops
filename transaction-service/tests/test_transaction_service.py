from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app, get_current_user

FAKE_USER = {"user_id": 1, "username": "testuser"}

client = TestClient(app, raise_server_exceptions=False)


# ── Fixtures ───────────────────────────────────────────────
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


def make_account_row(**overrides):
    base = {
        "account_id": 1,
        "balance": 500.0,
        "is_active": True,
        "user_id": 1,
    }
    return {**base, **overrides}


def make_txn_row(**overrides):
    base = {
        "id": 1,
        "type": "DEPOSIT",
        "amount": 100.0,
        "balance_after": 600.0,
        "created_at": datetime.now(),
        "reference_id": "abc123",
    }
    return {**base, **overrides}


# ═══════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════
def test_health():
    res = client.get("/transactions/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ═══════════════════════════════════════════════
# DEPOSIT
# ═══════════════════════════════════════════════
class TestDeposit:

    @patch("main.get_conn")
    def test_deposit_success(self, mock_get_conn):
        conn, cur = make_mock_conn()
        mock_get_conn.return_value = conn

        cur.fetchone.side_effect = [
            make_account_row(),
            make_txn_row(balance_after=600.0)
        ]

        res = client.post(
            "/transactions/deposit",
            json={"account_id": 1, "amount": 100}
        )

        assert res.status_code == 201
        assert res.json()["balance_after"] == 600.0

    @patch("main.get_conn")
    def test_deposit_account_not_found(self, mock_get_conn):
        conn, cur = make_mock_conn(fetchone=None)
        mock_get_conn.return_value = conn

        res = client.post(
            "/transactions/deposit",
            json={"account_id": 999, "amount": 100}
        )

        assert res.status_code == 404

    @patch("main.get_conn")
    def test_deposit_wrong_owner(self, mock_get_conn):
        conn, cur = make_mock_conn(fetchone=make_account_row(user_id=2))
        mock_get_conn.return_value = conn

        res = client.post(
            "/transactions/deposit",
            json={"account_id": 1, "amount": 100}
        )

        assert res.status_code == 403

    @patch("main.get_conn")
    def test_deposit_inactive_account(self, mock_get_conn):
        conn, cur = make_mock_conn(fetchone=make_account_row(is_active=False))
        mock_get_conn.return_value = conn

        res = client.post(
            "/transactions/deposit",
            json={"account_id": 1, "amount": 100}
        )

        assert res.status_code == 403

    def test_deposit_invalid_amount(self):
        res = client.post(
            "/transactions/deposit",
            json={"account_id": 1, "amount": -10}
        )
        assert res.status_code == 422


# ═══════════════════════════════════════════════
# WITHDRAW
# ═══════════════════════════════════════════════
class TestWithdraw:

    @patch("main.get_conn")
    def test_withdraw_success(self, mock_get_conn):
        conn, cur = make_mock_conn()
        mock_get_conn.return_value = conn

        cur.fetchone.side_effect = [
            make_account_row(balance=500.0),
            make_txn_row(type="WITHDRAW", balance_after=400.0)
        ]

        res = client.post(
            "/transactions/withdraw",
            json={"account_id": 1, "amount": 100}
        )

        assert res.status_code == 201
        assert res.json()["balance_after"] == 400.0

    @patch("main.get_conn")
    def test_withdraw_insufficient_funds(self, mock_get_conn):
        conn, cur = make_mock_conn(fetchone=make_account_row(balance=50.0))
        mock_get_conn.return_value = conn

        res = client.post(
            "/transactions/withdraw",
            json={"account_id": 1, "amount": 100}
        )

        assert res.status_code == 422

    @patch("main.get_conn")
    def test_withdraw_account_not_found(self, mock_get_conn):
        conn, cur = make_mock_conn(fetchone=None)
        mock_get_conn.return_value = conn

        res = client.post(
            "/transactions/withdraw",
            json={"account_id": 999, "amount": 100}
        )

        assert res.status_code == 404


# ═══════════════════════════════════════════════
# TRANSACTION HISTORY (FIXED)
# ═══════════════════════════════════════════════
class TestTransactionHistory:

    @patch("main.get_conn")
    def test_history_success(self, mock_get_conn):
        rows = [
            make_txn_row(id=1, amount=100),
            make_txn_row(id=2, amount=50),
        ]

        conn, cur = make_mock_conn()
        mock_get_conn.return_value = conn

        # ✅ FIX: generator to avoid StopIteration
        def fake_fetchone():
            yield make_account_row()
            yield {"total": 2}
            while True:
                yield {"total": 2}

        gen = fake_fetchone()
        cur.fetchone.side_effect = lambda: next(gen)

        cur.fetchall.return_value = rows

        res = client.get("/transactions/1")

        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        assert len(body["transactions"]) == 2

    @patch("main.get_conn")
    def test_history_account_not_found(self, mock_get_conn):
        conn, cur = make_mock_conn(fetchone=None)
        mock_get_conn.return_value = conn

        res = client.get("/transactions/999")
        assert res.status_code == 404

    @patch("main.get_conn")
    def test_history_wrong_owner(self, mock_get_conn):
        conn, cur = make_mock_conn(fetchone=make_account_row(user_id=2))
        mock_get_conn.return_value = conn

        res = client.get("/transactions/1")
        assert res.status_code == 403

    @patch("main.get_conn")
    def test_history_db_error(self, mock_get_conn):
        conn, cur = make_mock_conn()
        cur.execute.side_effect = Exception("db error")
        mock_get_conn.return_value = conn

        res = client.get("/transactions/1")
        assert res.status_code == 500
