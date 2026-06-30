import os
import sys

# ── FORCE PATH FIRST (CRITICAL) ─────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ── VERIFY PATH (DEBUG — optional, remove later) ────────
# print("PYTHONPATH:", sys.path)

# ── ENV VARS ────────────────────────────────────────────
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-ci-only")
os.environ.setdefault("JWT_EXPIRE_HOURS", "1")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("DB_USER", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpass")
