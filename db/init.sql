-- ============================================================
-- banking-app :: PostgreSQL Schema
-- Designed for stateless microservices + Kubernetes deployment
-- ============================================================

BEGIN;

-- ============================================================
-- EXTENSIONS
-- ============================================================
-- pgcrypto → used for UUID generation (preferred over uuid-ossp)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- USERS
-- Owned by: auth-service, account-service
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50)  UNIQUE NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(100),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ACCOUNTS
-- Owned by: account-service, balance-service
-- ============================================================
CREATE TABLE IF NOT EXISTS accounts (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Use UUID instead of RANDOM() to guarantee uniqueness
    account_number  VARCHAR(50) UNIQUE NOT NULL DEFAULT gen_random_uuid()::TEXT,

    account_type    VARCHAR(20) NOT NULL DEFAULT 'checking'
                        CHECK (account_type IN ('checking', 'savings')),

    balance         NUMERIC(14, 2) NOT NULL DEFAULT 0.00
                        CHECK (balance >= 0),

    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TRANSACTIONS (Append-only ledger — never update/delete)
-- Owned by: transaction-service
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    account_id      INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,

    type            VARCHAR(10) NOT NULL
                        CHECK (type IN ('DEPOSIT', 'WITHDRAW')),

    amount          NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    balance_after   NUMERIC(14, 2) NOT NULL,

    description     TEXT,

    -- Idempotency key (must be UNIQUE)
    reference_id    UUID UNIQUE DEFAULT gen_random_uuid(),

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES (Optimized for read-heavy workloads)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_accounts_user_id
    ON accounts(user_id);

CREATE INDEX IF NOT EXISTS idx_transactions_account
    ON transactions(account_id);

CREATE INDEX IF NOT EXISTS idx_transactions_created
    ON transactions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email);

-- ============================================================
-- TRIGGER FUNCTION (Auto-update updated_at)
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGERS (Idempotent creation)
-- ============================================================

-- Users trigger
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_users_updated_at'
    ) THEN
        CREATE TRIGGER trg_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
END $$;

-- Accounts trigger
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_accounts_updated_at'
    ) THEN
        CREATE TRIGGER trg_accounts_updated_at
        BEFORE UPDATE ON accounts
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
END $$;

-- ============================================================
-- END OF SCHEMA
-- ============================================================

COMMIT;
