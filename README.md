# VaultX Banking App

A production-style microservices banking application built for DevOps/Kubernetes portfolio demonstration.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         FRONTEND                               │
│              React 18 + Axios  (Nginx, port 80)                │
└───────┬────────────┬──────────────┬──────────────┬─────────────┘
        │            │              │              │
        ▼            ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ auth-service │ │ account- │ │ balance- │ │ transaction- │
│  :8001       │ │ service  │ │ service  │ │ service      │
│              │ │  :8002   │ │  :8003   │ │  :8004       │
│ /auth/login  │ │ /accounts│ │ /balance │ │ /transactions│
│ /auth/register│ │ /accounts│ │ /balance/│ │ /deposit     │
│ /auth/verify │ │  /me     │ │  {id}    │ │ /withdraw    │
└──────┬───────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘
       │              │             │               │
       └──────────────┴─────────────┴───────────────┘
                                │
                    ┌───────────▼───────────┐
                    │      PostgreSQL        │
                    │   users / accounts /   │
                    │    transactions        │
                    └───────────────────────┘
```

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Frontend    | React 18, React Router 6, Axios     |
| Backend     | Python 3.12, FastAPI, Uvicorn       |
| Database    | PostgreSQL 16                       |
| Auth        | JWT (HS256, bcrypt passwords)       |
| Containerisation | Docker, multi-stage builds     |
| Prod target | Kubernetes (stateless services)     |

## Service Ports

| Service             | Port |
|---------------------|------|
| auth-service        | 8001 |
| account-service     | 8002 |
| balance-service     | 8003 |
| transaction-service | 8004 |
| frontend            | 3000 (dev) / 80 (container) |
| postgres            | 5432 |

## Quick Start

### With Docker Compose (recommended)

```bash
docker compose up --build
```

Then open http://localhost:3000

### Without Docker (local dev)

1. Start Postgres and run `db/init.sql`

2. Set environment variables (or export them):
   ```bash
   export DB_HOST=localhost DB_PORT=5432 DB_NAME=bankapp \
          DB_USER=postgres DB_PASSWORD=postgres \
          JWT_SECRET=dev-secret
   ```

3. Start each service:
   ```bash
   # auth-service
   cd auth-service && pip install -r requirements.txt
   uvicorn main:app --port 8001 --reload

   # account-service
   cd account-service && pip install -r requirements.txt
   uvicorn main:app --port 8002 --reload

   # balance-service
   cd balance-service && pip install -r requirements.txt
   uvicorn main:app --port 8003 --reload

   # transaction-service
   cd transaction-service && pip install -r requirements.txt
   uvicorn main:app --port 8004 --reload

   # frontend
   cd frontend && npm install && npm run dev
   ```

4. Open http://localhost:3000

## Demo Credentials

```
Username: demo
Password: password123
```

## API Documentation

Each FastAPI service auto-generates interactive API docs:

- Auth:        http://localhost:8001/docs
- Account:     http://localhost:8002/docs
- Balance:     http://localhost:8003/docs
- Transaction: http://localhost:8004/docs

## Key Design Decisions

### Stateless services
All backend services are stateless — JWT is validated locally in each service using the shared `JWT_SECRET`. No session state in memory. Safe to run N replicas on Kubernetes with zero-downtime rolling deploys.

### Row-level locking on transactions
`transaction-service` uses `SELECT ... FOR UPDATE` in Postgres. Prevents double-spend race conditions when running multiple replicas concurrently.

### Append-only ledger
The `transactions` table is never updated or deleted — it's a financial ledger. Balance is derived from the `accounts.balance` column which is updated atomically.

### Non-root Docker containers
All service Dockerfiles create a non-root `appuser`. This is a security requirement in most production Kubernetes environments.

### Multi-stage frontend build
The frontend Dockerfile uses Node to build and Nginx to serve. Final image is ~25MB with no Node.js in it.

## Environment Variables

All services accept these environment variables (inject via K8s ConfigMap + Secret):

| Variable          | Default                         | Notes                            |
|-------------------|---------------------------------|----------------------------------|
| `DB_HOST`         | `localhost`                     | Postgres hostname                |
| `DB_PORT`         | `5432`                          |                                  |
| `DB_NAME`         | `bankapp`                       |                                  |
| `DB_USER`         | `postgres`                      |                                  |
| `DB_PASSWORD`     | `postgres`                      | Use K8s Secret                   |
| `JWT_SECRET`      | `change-me-...`                 | **Must change in production**    |
| `JWT_EXPIRE_HOURS`| `24`                            | auth-service only                |

Frontend (Vite build-time):

| Variable                 | Default                   |
|--------------------------|---------------------------|
| `VITE_AUTH_URL`          | `http://localhost:8001`   |
| `VITE_ACCOUNT_URL`       | `http://localhost:8002`   |
| `VITE_BALANCE_URL`       | `http://localhost:8003`   |
| `VITE_TRANSACTION_URL`   | `http://localhost:8004`   |

## Folder Structure

```
banking-app/
├── db/
│   └── init.sql                # PostgreSQL schema + seed data
├── auth-service/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── account-service/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── balance-service/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── transaction-service/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/client.js        # Axios + token management
│   │   ├── context/AuthContext.jsx
│   │   ├── pages/Login.jsx
│   │   ├── pages/Dashboard.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   ├── nginx.conf
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```
