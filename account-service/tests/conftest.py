"""conftest.py — account-service"""
import os
import sys

os.environ["JWT_SECRET"]  = "test-secret-key-for-ci-only"
os.environ["DB_HOST"]     = "localhost"
os.environ["DB_PORT"]     = "5432"
os.environ["DB_NAME"]     = "testdb"
os.environ["DB_USER"]     = "testuser"
os.environ["DB_PASSWORD"] = "testpass"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
