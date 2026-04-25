"""
test_transaction_service.py
===========================
Full pytest test suite for the BankApp transaction-service.

Endpoints covered:
  GET  /transactions/health          — liveness probe
  POST /transactions/deposit         — credit funds (auth required)
  POST /transactions/withdraw        — debit funds  (auth required)
  GET  /transactions/{account_id}    — paginated history (auth + ownership)

Coverage targets: ≥ 90 % line + branch (SonarQube Quality Gate: PASS)

Mock contract — each mock row matches the EXACT columns of its SQL query:

  _get_account_locked  →  SELECT a.id, a.balance, a.is_active, a.user_id
  RETURNING (deposit/withdraw) →  id, type, amount, balance_after,
                                  created_at, reference_id
  Ownership check (history) →  SELECT user_id FROM accounts
  COUNT query (history)     →  SELECT COUNT(*) as total FROM transactions
  History rows (history)    →  id, type, amount, balance_after,
                               description, reference_id, created_at

Run (from the service directory, conftest.py patches sys.path):
  pytest tests/test_transaction_service.py -v --cov=main --cov-report=term-missing
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import jwt
import pytest
from fastapi.testclient import TestClient

# ── JWT_SECRET must be set before main.py is imported ─────────────────────────
# conftest.py sets DB_* vars and patches sys.path; JWT is needed here too.
_TEST_JWT_SECRET = "test-secret-for-ci"
os.environ.setdefault("JWT_SECRET", _TEST_JWT_SECRET)
os.environ.setdefault("DB_HOST",     "localhost")
os.environ.setdefault("DB_PORT",     "5432")
os.environ.setdefault("DB_NAME",     "testdb")
os.environ.setdefault("DB_USER",     "testuser")
os.environ.setdefault("DB_PASSWORD", "testpass")

from main import JWT_ALGO, app, get_current_user  # noqa: E402

# Re-read from the live module so the secret is always in sync with the app
from main import JWT_SECRET as _APP_SECRET  # noqa: E402

_TEST_JWT_SECRET = _APP_SECRET  # single source of truth; never drift


# ══════════════════════════════════════════════════════════════════════════════
# ── Shared constants & client ──────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

FAKE_USER     = {"user_id": 1, "username": "testuser"}
FAKE_USER_ALT = {"user_id": 2, "username": "otheruser"}

client = TestClient(app, raise_server_exceptions=False)


# ══════════════════════════════════════════════════════════════════════════════
# ── JWT helpers ────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _make_token(user_id: int = 1, username: str = "testuser",
                expire_delta: timedelta = timedelta(hours=24)) -> str:
    payload = {
        "sub":      str(user_id),
        "username": username,
        "exp":      datetime.now(timezone.utc) + expire_delta,
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm=JWT_ALGO)


def _expired_token() -> str:
    return _make_token(expire_delta=timedelta(hours=-1))


def _invalid_token() -> str:
    return jwt.encode(
        {"sub": "1", "username": "x",
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "TOTALLY_WRONG_SECRET",
        algorithm=JWT_ALGO,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ── Mock-row factories  (field sets match the SQL SELECTs exactly) ─────────────
# ══════════════════════════════════════════════════════════════════════════════

def _account_locked_row(**kw) -> dict:
    """
    Matches: SELECT a.id, a.balance, a.is_active, a.user_id
             FROM accounts a WHERE a.id = %s FOR UPDATE
    Used by: _get_account_locked  →  deposit, withdraw
    """
    return {"id": 1, "balance": 500.0, "is_active": True, "user_id": 1, **kw}


def _txn_returning_row(txn_type: str = "DEPOSIT", amount: float = 100.0,
                       balance_after: float = 600.0, **kw) -> dict:
    """
    Matches: RETURNING id, type, amount, balance_after, created_at, reference_id
    Used by: deposit, withdraw  (second fetchone)
    """
    return {
        "id":            101,
        "type":          txn_type,
        "amount":        amount,
        "balance_after": balance_after,
        "created_at":    datetime(2024, 6, 1, 12, 0, 0),
        "reference_id":  "ref-abc-123",
        **kw,
    }


def _history_ownership_row(user_id: int = 1) -> dict:
    """
    Matches: SELECT user_id FROM accounts WHERE id = %s
    Used by: transaction_history  (first fetchone)
    """
    return {"user_id": user_id}


def _history_count_row(total: int = 0) -> dict:
    """
    Matches: SELECT COUNT(*) as total FROM transactions WHERE account_id = %s
    Used by: transaction_history  (second fetchone, after fetchall)
    """
    return {"total": total}


def _history_txn_row(txn_id: int = 1, txn_type: str = "DEPOSIT",
                     amount: float = 100.0, balance_after: float = 600.0,
                     description: str | None = None, **kw) -> dict:
    """
    Matches: SELECT id, type, amount, balance_after, description,
                    reference_id, created_at
             FROM transactions WHERE account_id = %s
    Used by: transaction_history  (fetchall)
    """
    return {
        "id":            txn_id,
        "type":          txn_type,
        "amount":        amount,
        "balance_after": balance_after,
        "description":   description,
        "reference_id":  "ref-abc-123",
        "created_at":    datetime(2024, 6, 1, 12, 0, 0),
        **kw,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ── Mock-connection factory ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _make_conn(fetchone_seq: list | None = None,
               fetchall_rows: list | None = None,
               execute_raises: Exception | None = None):
    """
    Build a (conn, cur) pair whose fetchone() is consumed from fetchone_seq
    in order (side_effect list — exhausted entries raise StopIteration,
    making accidental extra calls immediately visible as a test failure).

    Args:
        fetchone_seq:   ordered list of dicts returned by successive fetchone() calls.
        fetchall_rows:  rows returned by fetchall().
        execute_raises: if set, cur.execute() raises this exception on every call.
    """
    conn = MagicMock()
    cur  = MagicMock()
    conn.cursor.return_value = cur
    conn.autocommit          = False

    if execute_raises:
        cur.execute.side_effect = execute_raises
    if fetchone_seq is not None:
        cur.fetchone.side_effect = fetchone_seq   # list: consumed one-by-one
    cur.fetchall.return_value = fetchall_rows or []

    return conn, cur


# ══════════════════════════════════════════════════════════════════════════════
# ── Auth fixture ───────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _inject_auth():
    """Default: authenticated as FAKE_USER.  Auth tests clear this themselves."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield
    app.dependency_overrides.clear()


# ══════════════════════════════════════════════════════════════════════════════
# ── pytest marks ───────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def pytest_configure(config):
    config.addinivalue_line("markers", "api: HTTP-level integration tests")
    config.addinivalue_line("markers", "unit: unit-level tests (no HTTP)")
    config.addinivalue_line("markers", "security: auth / JWT boundary tests")


# ══════════════════════════════════════════════════════════════════════════════
#  1.  GET /transactions/health
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.api()
class TestHealth:
    """Liveness probe — no auth, no DB."""

    def test_returns_200(self):
        resp = client.get("/transactions/health")
        assert resp.status_code == 200

    def test_response_contract(self):
        body = client.get("/transactions/health").json()
        assert body["status"]  == "ok"
        assert body["service"] == "transaction-service"

    def test_reachable_without_auth_header(self):
        """Health must respond even when Authorization header is absent."""
        app.dependency_overrides.clear()
        resp = client.get("/transactions/health")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
#  2.  POST /transactions/deposit
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.api()
class TestDeposit:
    """
    fetchone sequence inside deposit():
      call 1 — _get_account_locked  →  account row
      call 2 — INSERT … RETURNING   →  txn row
    """

    # ── 2a. Success paths ──────────────────────────────────────────────────────

    @patch("main.get_conn")
    def test_success_returns_201(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(amount=100.0, balance_after=600.0),
        ])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 100.0})

        assert resp.status_code == 201

    @patch("main.get_conn")
    def test_response_body_shape(self, mock_conn):
        """All six contract fields must be present in the response."""
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(),
        ])
        mock_conn.return_value = conn

        body = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 100.0}).json()

        for field in ("transaction_id", "reference_id", "type",
                      "amount", "balance_after", "created_at"):
            assert field in body, f"missing field: {field}"

    @patch("main.get_conn")
    def test_type_is_deposit(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(txn_type="DEPOSIT"),
        ])
        mock_conn.return_value = conn

        body = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 100.0}).json()
        assert body["type"] == "DEPOSIT"

    @patch("main.get_conn")
    def test_balance_after_is_reflected_from_db(self, mock_conn):
        """balance_after comes from RETURNING — test it is passed through."""
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(balance=250.0),
            _txn_returning_row(amount=75.0, balance_after=325.0),
        ])
        mock_conn.return_value = conn

        body = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 75.0}).json()
        assert body["balance_after"] == pytest.approx(325.0)

    @patch("main.get_conn")
    def test_optional_description_accepted(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(),
        ])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 50.0,
                                 "description": "Salary payment"})
        assert resp.status_code == 201

    @patch("main.get_conn")
    def test_deposit_into_zero_balance_account(self, mock_conn):
        """Depositing into a $0 account must succeed — 0 is not falsy guard."""
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(balance=0.0),
            _txn_returning_row(amount=50.0, balance_after=50.0),
        ])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 50.0})
        assert resp.status_code == 201
        assert resp.json()["balance_after"] == pytest.approx(50.0)

    @patch("main.get_conn")
    def test_minimum_valid_amount(self, mock_conn):
        """$0.01 is the smallest legal deposit (Pydantic: amount > 0)."""
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(amount=0.01, balance_after=500.01),
        ])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 0.01})
        assert resp.status_code == 201

    @patch("main.get_conn")
    def test_large_amount_accepted(self, mock_conn):
        """No upper limit in business logic — large amounts must pass."""
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(amount=1_000_000.00, balance_after=1_000_500.00),
        ])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 1_000_000.00})
        assert resp.status_code == 201

    # ── 2b. Transaction guarantees ─────────────────────────────────────────────

    @patch("main.get_conn")
    def test_commit_called_on_success(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(),
        ])
        mock_conn.return_value = conn

        client.post("/transactions/deposit", json={"account_id": 1, "amount": 10.0})
        conn.commit.assert_called_once()

    @patch("main.get_conn")
    def test_close_called_on_success(self, mock_conn):
        """finally: conn.close() must always execute."""
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(),
        ])
        mock_conn.return_value = conn

        client.post("/transactions/deposit", json={"account_id": 1, "amount": 10.0})
        conn.close.assert_called_once()

    @patch("main.get_conn")
    def test_rollback_and_close_on_db_error(self, mock_conn):
        """Generic DB exception → rollback + close, then 500."""
        conn, cur = _make_conn(execute_raises=Exception("deadlock"))
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 10.0})

        assert resp.status_code == 500
        conn.rollback.assert_called()
        conn.close.assert_called_once()

    @patch("main.get_conn")
    def test_rollback_on_http_404_close_still_called(self, mock_conn):
        """
        HTTPException (404) → rollback called, re-raised as-is (not 500),
        close still called via finally.
        """
        conn, cur = _make_conn(fetchone_seq=[None])   # _get_account_locked → 404
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 999, "amount": 10.0})

        assert resp.status_code == 404            # original status preserved
        conn.rollback.assert_called()             # rollback IS triggered
        conn.close.assert_called_once()           # finally always runs

    @patch("main.get_conn")
    def test_rollback_on_http_403_close_still_called(self, mock_conn):
        """Same guarantee for 403 path."""
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(user_id=99)])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 10.0})

        assert resp.status_code == 403
        conn.rollback.assert_called()
        conn.close.assert_called_once()

    @patch("main.get_conn")
    def test_db_error_detail_is_generic(self, mock_conn):
        """500 detail must never leak internal error messages to the client."""
        conn, cur = _make_conn(execute_raises=Exception("pg password auth failed"))
        mock_conn.return_value = conn

        body = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 10.0}).json()

        assert body["detail"] == "Database error"
        assert "pg password auth" not in body["detail"]

    # ── 2c. Account / ownership errors ────────────────────────────────────────

    @patch("main.get_conn")
    def test_account_not_found_returns_404(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[None])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 999, "amount": 50.0})

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("main.get_conn")
    def test_wrong_owner_returns_403(self, mock_conn):
        """Account belongs to user_id=99; auth as user_id=1 → 403."""
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(user_id=99)])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 50.0})

        assert resp.status_code == 403
        assert "denied" in resp.json()["detail"].lower()

    @patch("main.get_conn")
    def test_inactive_account_returns_403(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(is_active=False)])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 50.0})

        assert resp.status_code == 403
        assert "inactive" in resp.json()["detail"].lower()

    # ── 2d. Pydantic input validation ─────────────────────────────────────────

    @pytest.mark.parametrize("amount", [0, -1, -0.01, -999])
    def test_non_positive_amount_returns_422(self, amount):
        """Validator: amount must be strictly positive."""
        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": amount})
        assert resp.status_code == 422

    @pytest.mark.parametrize("amount", [10.001, 0.001, 99.999])
    def test_more_than_2_decimal_places_returns_422(self, amount):
        """Validator: max 2 decimal places — round(v, 2) != v."""
        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": amount})
        assert resp.status_code == 422

    @pytest.mark.parametrize("amount", [0.01, 0.10, 1.50, 100.00, 9999.99])
    @patch("main.get_conn")
    def test_valid_2dp_amounts_pass_validation(self, mock_conn, amount):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(amount=amount),
        ])
        mock_conn.return_value = conn

        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": amount})
        assert resp.status_code == 201

    def test_missing_account_id_returns_422(self):
        resp = client.post("/transactions/deposit", json={"amount": 100.0})
        assert resp.status_code == 422

    def test_missing_amount_returns_422(self):
        resp = client.post("/transactions/deposit", json={"account_id": 1})
        assert resp.status_code == 422

    def test_empty_body_returns_422(self):
        resp = client.post("/transactions/deposit", json={})
        assert resp.status_code == 422

    def test_string_amount_returns_422(self):
        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": "lots"})
        assert resp.status_code == 422

    def test_null_amount_returns_422(self):
        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": None})
        assert resp.status_code == 422

    # ── 2e. Auth ──────────────────────────────────────────────────────────────

    def test_no_auth_header_returns_403(self):
        app.dependency_overrides.clear()
        resp = client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 10.0})
        assert resp.status_code == 403

    def test_expired_token_returns_401(self):
        app.dependency_overrides.clear()
        resp = client.post(
            "/transactions/deposit",
            json={"account_id": 1, "amount": 10.0},
            headers={"Authorization": f"Bearer {_expired_token()}"},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_invalid_token_returns_401(self):
        app.dependency_overrides.clear()
        resp = client.post(
            "/transactions/deposit",
            json={"account_id": 1, "amount": 10.0},
            headers={"Authorization": f"Bearer {_invalid_token()}"},
        )
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["detail"]

    def test_malformed_bearer_returns_401(self):
        app.dependency_overrides.clear()
        resp = client.post(
            "/transactions/deposit",
            json={"account_id": 1, "amount": 10.0},
            headers={"Authorization": "Bearer not.a.real.jwt"},
        )
        assert resp.status_code == 401

    def test_valid_jwt_is_accepted(self):
        """Real JWT with correct secret → request proceeds to DB mock."""
        app.dependency_overrides.clear()
        with patch("main.get_conn") as mock_conn:
            conn, cur = _make_conn(fetchone_seq=[
                _account_locked_row(),
                _txn_returning_row(),
            ])
            mock_conn.return_value = conn
            resp = client.post(
                "/transactions/deposit",
                json={"account_id": 1, "amount": 10.0},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )
        assert resp.status_code == 201


# ══════════════════════════════════════════════════════════════════════════════
#  3.  POST /transactions/withdraw
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestWithdraw:
    """
    fetchone sequence inside withdraw():
      call 1 — _get_account_locked  →  account row
      call 2 — INSERT … RETURNING   →  txn row   (only on sufficient funds)
    """

    # ── 3a. Success paths ──────────────────────────────────────────────────────

    @patch("main.get_conn")
    def test_success_returns_201(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(balance=500.0),
            _txn_returning_row(txn_type="WITHDRAW", amount=100.0,
                               balance_after=400.0),
        ])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 100.0})
        assert resp.status_code == 201

    @patch("main.get_conn")
    def test_type_is_withdraw(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(txn_type="WITHDRAW"),
        ])
        mock_conn.return_value = conn

        body = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 10.0}).json()
        assert body["type"] == "WITHDRAW"

    @patch("main.get_conn")
    def test_balance_after_is_correct(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(balance=300.0),
            _txn_returning_row(txn_type="WITHDRAW", amount=125.0,
                               balance_after=175.0),
        ])
        mock_conn.return_value = conn

        body = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 125.0}).json()
        assert body["balance_after"] == pytest.approx(175.0)

    @patch("main.get_conn")
    def test_withdraw_exact_balance_succeeds(self, mock_conn):
        """$500.00 from $500.00 — exact withdrawal; NOT insufficient funds."""
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(balance=500.0),
            _txn_returning_row(txn_type="WITHDRAW", amount=500.0,
                               balance_after=0.0),
        ])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 500.0})
        assert resp.status_code == 201
        assert resp.json()["balance_after"] == pytest.approx(0.0)

    @patch("main.get_conn")
    def test_optional_description_accepted(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(txn_type="WITHDRAW"),
        ])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 10.0,
                                 "description": "Rent payment"})
        assert resp.status_code == 201

    # ── 3b. Insufficient funds ─────────────────────────────────────────────────

    @patch("main.get_conn")
    def test_insufficient_funds_returns_422(self, mock_conn):
        """amount > balance → 422 (HTTPException raised inside withdraw)."""
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(balance=50.0)])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 100.0})

        assert resp.status_code == 422
        assert "Insufficient" in resp.json()["detail"]

    @patch("main.get_conn")
    def test_insufficient_funds_shows_available_balance(self, mock_conn):
        """Error detail must display the actual available balance for UX."""
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(balance=42.50)])
        mock_conn.return_value = conn

        detail = client.post("/transactions/withdraw",
                             json={"account_id": 1, "amount": 100.0}).json()["detail"]
        assert "42.50" in detail

    @patch("main.get_conn")
    def test_withdraw_from_zero_balance_returns_422(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(balance=0.0)])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 0.01})
        assert resp.status_code == 422

    @patch("main.get_conn")
    def test_one_cent_over_balance_is_rejected(self, mock_conn):
        """$100.01 from $100.00 — no overdraft, even by one cent."""
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(balance=100.0)])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 100.01})
        assert resp.status_code == 422

    # ── 3c. Transaction guarantees ─────────────────────────────────────────────

    @patch("main.get_conn")
    def test_commit_called_on_success(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(txn_type="WITHDRAW"),
        ])
        mock_conn.return_value = conn

        client.post("/transactions/withdraw",
                    json={"account_id": 1, "amount": 10.0})
        conn.commit.assert_called_once()

    @patch("main.get_conn")
    def test_close_called_on_success(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(txn_type="WITHDRAW"),
        ])
        mock_conn.return_value = conn

        client.post("/transactions/withdraw",
                    json={"account_id": 1, "amount": 10.0})
        conn.close.assert_called_once()

    @patch("main.get_conn")
    def test_rollback_and_close_on_db_error(self, mock_conn):
        conn, cur = _make_conn(execute_raises=Exception("connection reset"))
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 10.0})

        assert resp.status_code == 500
        conn.rollback.assert_called()
        conn.close.assert_called_once()

    @patch("main.get_conn")
    def test_insufficient_funds_triggers_rollback(self, mock_conn):
        """422 from insufficient funds is an HTTPException → rollback called."""
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(balance=1.0)])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 100.0})

        assert resp.status_code == 422
        conn.rollback.assert_called()
        conn.close.assert_called_once()

    @patch("main.get_conn")
    def test_no_commit_on_insufficient_funds(self, mock_conn):
        """Rollback path must never call commit."""
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(balance=1.0)])
        mock_conn.return_value = conn

        client.post("/transactions/withdraw",
                    json={"account_id": 1, "amount": 100.0})
        conn.commit.assert_not_called()

    # ── 3d. Account / ownership errors ────────────────────────────────────────

    @patch("main.get_conn")
    def test_account_not_found_returns_404(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[None])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 999, "amount": 10.0})
        assert resp.status_code == 404

    @patch("main.get_conn")
    def test_wrong_owner_returns_403(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(user_id=99)])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 10.0})
        assert resp.status_code == 403

    @patch("main.get_conn")
    def test_inactive_account_returns_403(self, mock_conn):
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(is_active=False)])
        mock_conn.return_value = conn

        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 10.0})
        assert resp.status_code == 403

    # ── 3e. Pydantic validation ────────────────────────────────────────────────

    @pytest.mark.parametrize("amount", [0, -1, -0.01])
    def test_non_positive_amount_returns_422(self, amount):
        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": amount})
        assert resp.status_code == 422

    @pytest.mark.parametrize("amount", [10.001, 5.999])
    def test_excess_decimal_places_returns_422(self, amount):
        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": amount})
        assert resp.status_code == 422

    def test_missing_amount_returns_422(self):
        resp = client.post("/transactions/withdraw", json={"account_id": 1})
        assert resp.status_code == 422

    def test_missing_account_id_returns_422(self):
        resp = client.post("/transactions/withdraw", json={"amount": 10.0})
        assert resp.status_code == 422

    # ── 3f. Auth ──────────────────────────────────────────────────────────────

    def test_no_auth_header_returns_403(self):
        app.dependency_overrides.clear()
        resp = client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 10.0})
        assert resp.status_code == 403

    def test_expired_token_returns_401(self):
        app.dependency_overrides.clear()
        resp = client.post(
            "/transactions/withdraw",
            json={"account_id": 1, "amount": 10.0},
            headers={"Authorization": f"Bearer {_expired_token()}"},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_invalid_token_returns_401(self):
        app.dependency_overrides.clear()
        resp = client.post(
            "/transactions/withdraw",
            json={"account_id": 1, "amount": 10.0},
            headers={"Authorization": f"Bearer {_invalid_token()}"},
        )
        assert resp.status_code == 401

    def test_valid_jwt_is_accepted(self):
        app.dependency_overrides.clear()
        with patch("main.get_conn") as mock_conn:
            conn, cur = _make_conn(fetchone_seq=[
                _account_locked_row(),
                _txn_returning_row(txn_type="WITHDRAW"),
            ])
            mock_conn.return_value = conn
            resp = client.post(
                "/transactions/withdraw",
                json={"account_id": 1, "amount": 10.0},
                headers={"Authorization": f"Bearer {_make_token()}"},
            )
        assert resp.status_code == 201


# ══════════════════════════════════════════════════════════════════════════════
#  4.  GET /transactions/{account_id}   —  history + pagination
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestTransactionHistory:
    """
    fetchone sequence inside transaction_history():
      call 1 — SELECT user_id FROM accounts (ownership check)
      call 2 — SELECT COUNT(*) as total FROM transactions
    fetchall — transaction rows (between the two fetchone calls)
    """

    # ── helper: wire conn for success path ────────────────────────────────────
    @staticmethod
    def _success_conn(rows: list, total: int | None = None,
                      owner_user_id: int = 1):
        conn, cur = _make_conn(
            fetchone_seq=[
                _history_ownership_row(user_id=owner_user_id),
                _history_count_row(total=total if total is not None else len(rows)),
            ],
            fetchall_rows=rows,
        )
        return conn, cur

    # ── 4a. Success paths ──────────────────────────────────────────────────────

    @patch("main.get_conn")
    def test_success_returns_200(self, mock_conn):
        conn, cur = self._success_conn([_history_txn_row(), _history_txn_row(txn_id=2)])
        mock_conn.return_value = conn

        resp = client.get("/transactions/1")
        assert resp.status_code == 200

    @patch("main.get_conn")
    def test_response_envelope_shape(self, mock_conn):
        """Top-level response must contain all five envelope fields."""
        conn, cur = self._success_conn([_history_txn_row()], total=1)
        mock_conn.return_value = conn

        body = client.get("/transactions/1").json()

        assert body["account_id"]    == 1
        assert body["total"]         == 1
        assert body["limit"]         == 20      # default
        assert body["offset"]        == 0       # default
        assert isinstance(body["transactions"], list)

    @patch("main.get_conn")
    def test_each_txn_has_required_fields(self, mock_conn):
        """Every transaction object must carry all seven fields."""
        conn, cur = self._success_conn([_history_txn_row()])
        mock_conn.return_value = conn

        txn = client.get("/transactions/1").json()["transactions"][0]

        for field in ("id", "type", "amount", "balance_after",
                      "description", "reference_id", "created_at"):
            assert field in txn, f"missing transaction field: {field}"

    @patch("main.get_conn")
    def test_correct_number_of_rows_returned(self, mock_conn):
        rows = [_history_txn_row(txn_id=i) for i in range(1, 4)]
        conn, cur = self._success_conn(rows, total=3)
        mock_conn.return_value = conn

        body = client.get("/transactions/1").json()
        assert len(body["transactions"]) == 3

    @patch("main.get_conn")
    def test_empty_history_returns_200_with_empty_list(self, mock_conn):
        """Account with no transactions → 200 + empty list + total=0."""
        conn, cur = self._success_conn([], total=0)
        mock_conn.return_value = conn

        body = client.get("/transactions/1").json()
        assert body["transactions"] == []
        assert body["total"] == 0

    @patch("main.get_conn")
    def test_description_none_serialised_as_null(self, mock_conn):
        """NULL description from DB should appear as null (None) in JSON."""
        conn, cur = self._success_conn([_history_txn_row(description=None)])
        mock_conn.return_value = conn

        txn = client.get("/transactions/1").json()["transactions"][0]
        assert txn["description"] is None

    @patch("main.get_conn")
    def test_description_string_serialised_correctly(self, mock_conn):
        """Non-null description flows through unchanged."""
        conn, cur = self._success_conn(
            [_history_txn_row(description="Direct debit")]
        )
        mock_conn.return_value = conn

        txn = client.get("/transactions/1").json()["transactions"][0]
        assert txn["description"] == "Direct debit"

    @patch("main.get_conn")
    def test_total_reflects_db_count_not_page_size(self, mock_conn):
        """total comes from COUNT(*), not len(rows) — they differ when paginated."""
        # 1 row returned (limit=1), but total=50 across all pages
        conn, cur = self._success_conn([_history_txn_row()], total=50)
        mock_conn.return_value = conn

        body = client.get("/transactions/1?limit=1&offset=0").json()
        assert body["total"] == 50
        assert len(body["transactions"]) == 1

    # ── 4b. Pagination ─────────────────────────────────────────────────────────

    @patch("main.get_conn")
    def test_default_limit_is_20(self, mock_conn):
        conn, cur = self._success_conn([])
        mock_conn.return_value = conn

        assert client.get("/transactions/1").json()["limit"] == 20

    @patch("main.get_conn")
    def test_default_offset_is_0(self, mock_conn):
        conn, cur = self._success_conn([])
        mock_conn.return_value = conn

        assert client.get("/transactions/1").json()["offset"] == 0

    @patch("main.get_conn")
    def test_custom_limit_and_offset_reflected(self, mock_conn):
        conn, cur = self._success_conn([], total=100)
        mock_conn.return_value = conn

        body = client.get("/transactions/1?limit=5&offset=40").json()
        assert body["limit"]  == 5
        assert body["offset"] == 40

    @pytest.mark.parametrize("limit,offset,expected", [
        (1,    0,   200),   # minimum valid limit
        (100,  0,   200),   # maximum valid limit
        (20,   999, 200),   # high offset — empty page is still 200
        (0,    0,   422),   # limit=0  violates ge=1
        (101,  0,   422),   # limit=101 violates le=100
        (20,  -1,   422),   # negative offset violates ge=0
    ])
    @patch("main.get_conn")
    def test_pagination_boundary_values(self, mock_conn, limit, offset, expected):
        """FastAPI Query constraints: limit ∈ [1,100], offset ≥ 0."""
        conn, cur = self._success_conn([])
        mock_conn.return_value = conn

        resp = client.get(f"/transactions/1?limit={limit}&offset={offset}")
        assert resp.status_code == expected

    # ── 4c. Ownership / not found ──────────────────────────────────────────────

    @patch("main.get_conn")
    def test_account_not_found_returns_404(self, mock_conn):
        """fetchone returns None on ownership check → 404."""
        conn, cur = _make_conn(fetchone_seq=[None])
        mock_conn.return_value = conn

        resp = client.get("/transactions/999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("main.get_conn")
    def test_wrong_owner_returns_403(self, mock_conn):
        """user_id mismatch on ownership check → 403."""
        conn, cur = _make_conn(fetchone_seq=[_history_ownership_row(user_id=99)])
        mock_conn.return_value = conn

        resp = client.get("/transactions/1")
        assert resp.status_code == 403
        assert "denied" in resp.json()["detail"].lower()

    @patch("main.get_conn")
    def test_http_exception_not_wrapped_as_500(self, mock_conn):
        """404 from ownership check must stay 404 — never swallowed as 500."""
        conn, cur = _make_conn(fetchone_seq=[None])
        mock_conn.return_value = conn

        resp = client.get("/transactions/999")
        assert resp.status_code == 404    # not 500

    # ── 4d. DB / server errors ─────────────────────────────────────────────────

    @patch("main.get_conn")
    def test_db_error_returns_500(self, mock_conn):
        conn, cur = _make_conn(execute_raises=Exception("DB unavailable"))
        mock_conn.return_value = conn

        resp = client.get("/transactions/1")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Database error"

    @patch("main.get_conn")
    def test_db_error_detail_is_generic(self, mock_conn):
        """Internal error message must not be exposed in 500 response."""
        conn, cur = _make_conn(
            execute_raises=Exception("FATAL: password authentication failed")
        )
        mock_conn.return_value = conn

        body = client.get("/transactions/1").json()
        assert "password authentication" not in body["detail"]

    # ── 4e. Path parameter validation ─────────────────────────────────────────

    def test_string_account_id_returns_422(self):
        """FastAPI rejects non-integer path param before any DB call."""
        resp = client.get("/transactions/abc")
        assert resp.status_code == 422

    def test_float_account_id_returns_422(self):
        resp = client.get("/transactions/1.5")
        assert resp.status_code == 422

    @patch("main.get_conn")
    def test_large_account_id_falls_through_to_404(self, mock_conn):
        """Massive valid integer — no row exists — 404."""
        conn, cur = _make_conn(fetchone_seq=[None])
        mock_conn.return_value = conn

        resp = client.get("/transactions/999999999")
        assert resp.status_code == 404

    # ── 4f. Auth ──────────────────────────────────────────────────────────────

    def test_no_auth_header_returns_403(self):
        app.dependency_overrides.clear()
        resp = client.get("/transactions/1")
        assert resp.status_code == 403

    def test_expired_token_returns_401(self):
        app.dependency_overrides.clear()
        resp = client.get(
            "/transactions/1",
            headers={"Authorization": f"Bearer {_expired_token()}"},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_invalid_token_returns_401(self):
        app.dependency_overrides.clear()
        resp = client.get(
            "/transactions/1",
            headers={"Authorization": f"Bearer {_invalid_token()}"},
        )
        assert resp.status_code == 401

    def test_valid_jwt_is_accepted(self):
        """Real JWT → ownership check runs normally."""
        app.dependency_overrides.clear()
        with patch("main.get_conn") as mock_conn:
            conn, cur = self._success_conn([_history_txn_row()])
            mock_conn.return_value = conn
            resp = client.get(
                "/transactions/1",
                headers={"Authorization": f"Bearer {_make_token(user_id=1)}"},
            )
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
#  5.  get_current_user — JWT branch coverage
#      (parametrized across all three protected endpoints)
# ══════════════════════════════════════════════════════════════════════════════

_PROTECTED = [
    ("POST", "/transactions/deposit",  {"account_id": 1, "amount": 10.0}),
    ("POST", "/transactions/withdraw", {"account_id": 1, "amount": 10.0}),
    ("GET",  "/transactions/1",        None),
]


@pytest.mark.security
class TestJWTBranchCoverage:
    """
    Exercises both exception branches in get_current_user across every
    protected endpoint to maximise branch coverage:
      jwt.ExpiredSignatureError  →  401 "Token expired"
      jwt.InvalidTokenError      →  401 "Invalid token"
    """

    @pytest.mark.parametrize("method,endpoint,body", _PROTECTED)
    def test_expired_token_on_all_endpoints(self, method, endpoint, body):
        app.dependency_overrides.clear()
        headers = {"Authorization": f"Bearer {_expired_token()}"}
        resp = (
            client.post(endpoint, json=body, headers=headers)
            if method == "POST"
            else client.get(endpoint, headers=headers)
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    @pytest.mark.parametrize("method,endpoint,body", _PROTECTED)
    def test_invalid_signature_on_all_endpoints(self, method, endpoint, body):
        app.dependency_overrides.clear()
        headers = {"Authorization": f"Bearer {_invalid_token()}"}
        resp = (
            client.post(endpoint, json=body, headers=headers)
            if method == "POST"
            else client.get(endpoint, headers=headers)
        )
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["detail"]

    @pytest.mark.parametrize("method,endpoint,body", _PROTECTED)
    def test_missing_auth_on_all_endpoints(self, method, endpoint, body):
        """No Authorization header → HTTPBearer returns 403 before any decode."""
        app.dependency_overrides.clear()
        resp = (
            client.post(endpoint, json=body)
            if method == "POST"
            else client.get(endpoint)
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("bad_token", [
        "garbage.token.value",
        "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0.",   # alg:none attack
        "a.b.c",
    ])
    def test_malformed_tokens_rejected(self, bad_token):
        """Various malformed token shapes must all yield 401, never 500."""
        app.dependency_overrides.clear()
        resp = client.post(
            "/transactions/deposit",
            json={"account_id": 1, "amount": 10.0},
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code in (401, 403)


# ══════════════════════════════════════════════════════════════════════════════
#  6.  _get_account_locked — internal helper branch matrix
#      (documented explicitly; covered indirectly via deposit / withdraw)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestGetAccountLockedBranches:
    """
    All four branches of _get_account_locked tested via the deposit
    endpoint so the helper's lines appear in coverage without the need
    to call the private function directly.
    """

    @patch("main.get_conn")
    def test_branch_not_found(self, mock_conn):
        """fetchone → None  ⟹  404."""
        conn, cur = _make_conn(fetchone_seq=[None])
        mock_conn.return_value = conn

        assert client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 10.0}
                           ).status_code == 404

    @patch("main.get_conn")
    def test_branch_wrong_user_id(self, mock_conn):
        """account.user_id ≠ current user  ⟹  403."""
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(user_id=999)])
        mock_conn.return_value = conn

        assert client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 10.0}
                           ).status_code == 403

    @patch("main.get_conn")
    def test_branch_is_active_false(self, mock_conn):
        """is_active=False  ⟹  403."""
        conn, cur = _make_conn(fetchone_seq=[_account_locked_row(is_active=False)])
        mock_conn.return_value = conn

        assert client.post("/transactions/withdraw",
                           json={"account_id": 1, "amount": 10.0}
                           ).status_code == 403

    @patch("main.get_conn")
    def test_branch_all_checks_pass_returns_account(self, mock_conn):
        """All guards pass  ⟹  account dict returned, deposit succeeds."""
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(user_id=1, is_active=True),
            _txn_returning_row(),
        ])
        mock_conn.return_value = conn

        assert client.post("/transactions/deposit",
                           json={"account_id": 1, "amount": 10.0}
                           ).status_code == 201


# ══════════════════════════════════════════════════════════════════════════════
#  7.  Security / injection edge cases
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestSecurityEdgeCases:

    @pytest.mark.parametrize("description", [
        "'; DROP TABLE transactions; --",
        "<script>alert(1)</script>",
        "A" * 500,
        "",
    ])
    @patch("main.get_conn")
    def test_deposit_description_injection_handled_safely(self, mock_conn,
                                                          description):
        """
        Malicious / edge-case descriptions flow to a parameterised query —
        service must never crash (no 500).
        """
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(),
        ])
        mock_conn.return_value = conn

        resp = client.post(
            "/transactions/deposit",
            json={"account_id": 1, "amount": 10.0, "description": description},
        )
        assert resp.status_code in (201, 422)   # never 500

    @pytest.mark.parametrize("description", [
        "'; DELETE FROM transactions; --",
        "\x00null\x00byte",
    ])
    @patch("main.get_conn")
    def test_withdraw_description_injection_handled_safely(self, mock_conn,
                                                           description):
        conn, cur = _make_conn(fetchone_seq=[
            _account_locked_row(),
            _txn_returning_row(txn_type="WITHDRAW"),
        ])
        mock_conn.return_value = conn

        resp = client.post(
            "/transactions/withdraw",
            json={"account_id": 1, "amount": 10.0, "description": description},
        )
        assert resp.status_code in (201, 422)