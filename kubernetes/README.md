# VaultX Banking Platform

A production-grade microservices banking application with a complete DevSecOps pipeline — CI/CD, GitOps, Kubernetes, and Infrastructure as Code.

---

## Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DEVELOPER WORKFLOW                              │
│                                                                         │
│   git push  ──►  Jenkins CI  ──►  Docker Hub  ──►  GitHub (GitOps)     │
│                                                          │               │
│                                                    ArgoCD watches        │
│                                                          │               │
│                                                    EKS Cluster           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                                │
│                                                                         │
│              AWS ALB (internet-facing, port 80)                         │
│                           │                                             │
│              Nginx  ──  frontend (:80)                                  │
│                           │                                             │
│         ┌─────────────────┼──────────────────┐──────────────┐          │
│         ▼                 ▼                  ▼               ▼          │
│   auth-service    account-service    balance-service  transaction-svc   │
│      :8001            :8002              :8003             :8004         │
│         └─────────────────┴──────────────────┴──────────────┘           │
│                                      │                                  │
│                          AWS RDS PostgreSQL                              │
│                    users / accounts / transactions                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        INFRASTRUCTURE LAYER                              │
│                                                                         │
│  AWS EKS (2 nodes)  ──  AWS RDS  ──  AWS ALB  ──  AWS VPC              │
│                Provisioned by Terraform                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer          | Technology                                          |
|----------------|-----------------------------------------------------|
| Frontend       | React 18, Vite, Axios, Nginx                        |
| Backend        | Python 3.12, FastAPI, Uvicorn                       |
| Database       | PostgreSQL 16 (AWS RDS)                             |
| Auth           | JWT HS256, bcrypt password hashing                  |
| Containers     | Docker (multi-stage builds, non-root user)          |
| Orchestration  | Kubernetes (AWS EKS)                                |
| CI             | Jenkins + Shared Library (Groovy)                   |
| CD             | ArgoCD (GitOps, auto-sync)                          |
| Registry       | Docker Hub                                          |
| IaC            | Terraform (EKS, RDS, VPC, ALB Controller)           |
| Security       | Trivy image scan, pip-audit, SonarQube, JWT secrets |

---

## Repository Structure

```
banking-microservices-devops-main/
│
├── auth-service/                   # FastAPI — login, register, JWT verify
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│       ├── conftest.py
│       └── test_auth_service.py
│
├── account-service/                # FastAPI — account management
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│
├── balance-service/                # FastAPI — balance queries
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│
├── transaction-service/            # FastAPI — deposit, withdraw, history
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│
├── frontend/                       # React 18 + Vite served by Nginx
│   ├── src/
│   ├── nginx.conf
│   ├── Dockerfile
│   └── Jenkinsfile
│
├── kubernetes/                     # GitOps source of truth — ArgoCD watches this
│   ├── namespace/
│   ├── secrets/
│   ├── configmaps/
│   ├── db-init-job/
│   ├── auth-service/
│   ├── account-service/
│   ├── balance-service/
│   ├── transaction-service/
│   ├── frontend/
│   └── ingress/
│
├── argocd/                         # ArgoCD Application + Project manifests
│   ├── bankapp-application.yaml
│   └── bankapp-project.yaml
│
├── Terraform/                      # AWS infrastructure as code
│   ├── environments/dev/
│   └── modules/
│       ├── eks/
│       ├── rds/
│       ├── vpc/
│       ├── security-groups/
│       └── alb-controller/
│
├── db/
│   └── init.sql                    # PostgreSQL schema — run once via K8s Job
│
├── docker-compose.yml              # Local development only
└── .env.example
```

---

## CI/CD Pipeline

### Flow

```
git push
    │
    ▼
Jenkins picks up branch
    │
    ├── Checkout        sets IMAGE_TAG = <git-sha>-<build-number>
    ├── Lint            flake8
    ├── Test            pytest + coverage threshold enforcement
    ├── Dep Scan        pip-audit (blocks known CVEs in requirements.txt)
    ├── SonarQube       quality gate (skipped on feature/* branches)
    ├── Docker Build    BuildKit + layer cache
    ├── Trivy Scan      fails build on CRITICAL or HIGH CVEs
    ├── Docker Push     skipped on feature/* branches
    ├── Approval Gate   manual gate on main branch only
    └── GitOps Update   yq patches image tag in deployment YAML
                            │
                       git push to main
                            │
                       ArgoCD detects diff (polls every 3 min)
                            │
                       Rolling update on EKS — zero downtime
```

### Branch Behaviour

| Branch       | Lint | Test | Push | Deploy | Approval |
|--------------|------|------|------|--------|----------|
| `feature/*`  | ✅   | ✅   | ❌   | ❌     | ❌       |
| `develop`    | ✅   | ✅   | ✅   | dev    | ❌       |
| `release/*`  | ✅   | ✅   | ✅   | qa     | ❌       |
| `main`       | ✅   | ✅   | ✅   | prod   | ✅       |

### Jenkinsfile (per service — 8 lines)

```groovy
@Library('vaultx-shared-lib@main') _

pythonMicroservicePipeline(
    serviceName         : 'auth-service',
    serviceDir          : 'auth-service',
    containerName       : 'auth-service',
    deploymentFile      : 'kubernetes/auth-service/auth-service-deployment.yaml',
    coverageThreshold   : 85,
    gitCredentialsId    : 'github-token',
    dockerCredentialsId : 'docker'
)
```

All logic (lint, test, scan, build, push, gitops) lives in the shared library. Nothing duplicated across services.

### Jenkins Credentials Required

| ID              | Type                | Used for                    |
|-----------------|---------------------|-----------------------------|
| `github-token`  | Username + password | Repo checkout + GitOps push |
| `docker`        | Username + password | Docker Hub image push       |
| `sonar-token`   | Secret text         | SonarQube quality gate      |

---

## Service Ports

| Service             | Port |
|---------------------|------|
| frontend (Nginx)    | 80   |
| auth-service        | 8001 |
| account-service     | 8002 |
| balance-service     | 8003 |
| transaction-service | 8004 |
| PostgreSQL (RDS)    | 5432 |

---

## API Reference

### Auth Service — `/auth`

| Method | Endpoint         | Auth | Description            |
|--------|------------------|------|------------------------|
| GET    | `/auth/health`   | ❌   | Liveness probe         |
| POST   | `/auth/register` | ❌   | Register + return JWT  |
| POST   | `/auth/login`    | ❌   | Login + return JWT     |
| GET    | `/auth/verify`   | ✅   | Validate Bearer token  |

### Account Service — `/accounts`

| Method | Endpoint                 | Auth | Description           |
|--------|--------------------------|------|-----------------------|
| GET    | `/accounts/health`       | ❌   | Liveness probe        |
| GET    | `/accounts/me`           | ✅   | List my accounts      |
| GET    | `/accounts/profile`      | ✅   | My user profile       |
| POST   | `/accounts`              | ✅   | Open new account      |
| DELETE | `/accounts/{account_id}` | ✅   | Close account (soft)  |

### Balance Service — `/balance`

| Method | Endpoint                | Auth | Description              |
|--------|-------------------------|------|--------------------------|
| GET    | `/balance/health`       | ❌   | Liveness probe           |
| GET    | `/balance`              | ✅   | All my balances          |
| GET    | `/balance/{account_id}` | ✅   | Single account balance   |

### Transaction Service — `/transactions`

| Method | Endpoint                     | Auth | Description          |
|--------|------------------------------|------|----------------------|
| GET    | `/transactions/health`       | ❌   | Liveness probe       |
| POST   | `/transactions/deposit`      | ✅   | Deposit funds        |
| POST   | `/transactions/withdraw`     | ✅   | Withdraw funds       |
| GET    | `/transactions/{account_id}` | ✅   | Transaction history  |

---

## Environment Variables

| Variable          | Source    | Description                              |
|-------------------|-----------|------------------------------------------|
| `DB_HOST`         | ConfigMap | RDS endpoint                             |
| `DB_PORT`         | ConfigMap | 5432                                     |
| `JWT_EXPIRE_HOURS`| ConfigMap | Token expiry in hours (default: 24)      |
| `DB_NAME`         | Secret    | Database name                            |
| `DB_USER`         | Secret    | Database username                        |
| `DB_PASSWORD`     | Secret    | Database password                        |
| `JWT_SECRET`      | Secret    | Signing key — minimum 64 chars in prod   |

---

## Local Development

```bash
# Start everything with Docker Compose
cp .env.example .env
# Edit .env with your values
docker compose up --build

# App: http://localhost:80
# Auth API docs:        http://localhost:8001/docs
# Account API docs:     http://localhost:8002/docs
# Balance API docs:     http://localhost:8003/docs
# Transaction API docs: http://localhost:8004/docs
```

---

## Running Tests

```bash
# Auth service
cd auth-service
pip install -r requirements.txt pytest pytest-cov httpx
pytest tests/ -v --cov=. --cov-report=term-missing

# Account service
cd account-service && pytest tests/ -v --cov=.

# Balance service
cd balance-service && pytest tests/ -v --cov=.

# Transaction service
cd transaction-service && pytest tests/ -v --cov=.
```

Tests use `unittest.mock` — no database or external services required. Runs on any machine with Python 3.12.

---

## Infrastructure — Terraform

```bash
cd Terraform/environments/dev

terraform init
terraform plan
terraform apply        # ~15 minutes

# Configure kubectl after apply
aws eks update-kubeconfig \
  --region ap-south-1 \
  --name $(terraform output -raw eks_cluster_name)

kubectl get nodes      # should show 2 nodes Ready
```

**What gets created:**

| Resource           | Details                              |
|--------------------|--------------------------------------|
| VPC                | Public + private subnets, NAT Gateway|
| EKS Cluster        | Managed node group, 2 nodes          |
| RDS PostgreSQL     | Private subnet, encrypted at rest    |
| ALB Controller     | Helm-installed, IRSA-enabled         |
| Security Groups    | Least-privilege between EKS and RDS  |

---

## Kubernetes Deployment

Apply in this order:

```bash
# 1. Namespace
kubectl apply -f kubernetes/namespace/namespace.yaml

# 2. Config
kubectl apply -f kubernetes/secrets/secrets.yaml
kubectl apply -f kubernetes/configmaps/configmaps.yaml
kubectl apply -f kubernetes/configmaps/db-init-configmap.yaml

# 3. Init database schema
kubectl apply -f kubernetes/db-init-job/db-init-job.yaml
kubectl wait --for=condition=complete job/db-init-job -n bankapp --timeout=120s

# 4. Services
kubectl apply -f kubernetes/auth-service/
kubectl apply -f kubernetes/account-service/
kubectl apply -f kubernetes/balance-service/
kubectl apply -f kubernetes/transaction-service/
kubectl apply -f kubernetes/frontend/

# 5. Ingress
kubectl apply -f kubernetes/ingress/ingress.yaml

# 6. Verify
kubectl get pods -n bankapp
kubectl get ingress -n bankapp
```

---

## ArgoCD — GitOps CD

### Install

```bash
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Expose UI
kubectl patch svc argocd-server -n argocd \
  -p '{"spec": {"type": "LoadBalancer"}}'

# Get admin password
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

### Connect and deploy

```bash
kubectl apply -f argocd/bankapp-project.yaml
kubectl apply -f argocd/bankapp-application.yaml

# Check status
kubectl get application bankapp -n argocd
```

### Useful commands

```bash
argocd app get bankapp          # full status
argocd app sync bankapp         # manual sync
argocd app diff bankapp         # what changed
argocd app history bankapp      # all deployments
argocd app rollback bankapp     # roll back one version
argocd app refresh bankapp --hard  # force re-read from git
```

---

## Generating a Production JWT Secret

```bash
# Generate
openssl rand -base64 64

# Store in Kubernetes (safe, idempotent)
kubectl create secret generic bankapp-backend-secret \
  --from-literal=JWT_SECRET="$(openssl rand -base64 64)" \
  --from-literal=DB_NAME="bankapp" \
  --from-literal=DB_USER="postgres" \
  --from-literal=DB_PASSWORD="your-rds-password" \
  -n bankapp \
  --dry-run=client -o yaml | kubectl apply -f -
```

Rules: minimum 32 chars, never commit to Git, must be identical across all services.

---

## Troubleshooting

```bash
# Pod not starting
kubectl describe pod <pod-name> -n bankapp
kubectl logs <pod-name> -n bankapp

# CrashLoopBackOff  → wrong DB_HOST, missing secret, schema not initialised
# Pending           → insufficient node resources
# ImagePullBackOff  → wrong image name or not pushed to registry

# ArgoCD out of sync
argocd app diff bankapp
argocd app sync bankapp

# Test DB connectivity from inside a pod
kubectl exec -it <pod-name> -n bankapp -- \
  python -c "import psycopg2; print('DB ok')"
```

---

## Key Design Decisions

**Stateless services** — JWT validated locally in each service using the shared `JWT_SECRET`. Safe to run multiple replicas with zero-downtime rolling deploys.

**Row-level locking** — `transaction-service` uses `SELECT ... FOR UPDATE`. Prevents double-spend race conditions across concurrent replicas.

**Append-only ledger** — `transactions` table is never updated or deleted. Balance stored in `accounts.balance`, updated atomically in the same DB transaction.

**Non-root containers** — all Dockerfiles run as a non-root user. Required for most production Kubernetes security policies.

**GitOps single source of truth** — `kubernetes/` is the only deploy mechanism. No manual `kubectl apply` in production. ArgoCD reverts any out-of-band changes automatically (`selfHeal: true`).

**Security scanning in CI** — Trivy blocks CRIT/HIGH CVEs before any image reaches the registry. pip-audit blocks known vulnerable Python dependencies at dependency install time.
