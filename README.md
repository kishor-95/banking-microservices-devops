# VaultX Banking Platform

A production-grade microservices banking application with a complete DevSecOps pipeline — CI/CD, GitOps, Kubernetes, and Infrastructure as Code.

> 🔗 **Live Demo:** https://techpluse.online

---
## Platform Architecture
![VaultX Banking Platform Architecture](docs/images/architecture-diagram.png)

---
## Screenshots

### Application

| Login | Register |
|---|---|
| ![Login](docs/images/login.png) | ![Register](docs/images/register.png) |

| Dashboard | HTTPS Secure |
|---|---|
| ![Dashboard](docs/images/dashboard.png) | ![HTTPS](docs/images/https-secure.png) |

---

### CI/CD — Jenkins Pipeline

**All 5 services passing:**

![Jenkins All Services](docs/images/jenkins-all-services.png)

**Stage view — every stage green (Checkout → Lint → Test → SonarQube → Docker Build → Trivy → Push → GitOps Update):**

| account-service | auth-service |
|---|---|
| ![Account](docs/images/jenkins-account-service-stages.png) | ![Auth](docs/images/jenkins-auth-service-stages.png) |

| balance-service | transaction-service |
|---|---|
| ![Balance](docs/images/jenkins-balance-service-stages.png) | ![Transaction](docs/images/jenkins-transaction-service-stages.png) |

![Frontend Stages](docs/images/jenkins-frontend-stages.png)

---

### Security — SonarQube

**All 5 services passed quality gate — 87–96% test coverage, 0 security issues:**

![SonarQube All Services](docs/images/sonarqube-all-services.png)

![SonarQube Auth Service Detail](docs/images/sonarqube-auth-service.png)

---

### Container Registry — Docker Hub

**CI pipeline pushes a new image tag (`<git-sha>-<build-number>`) on every successful main branch build:**

| account-service (19 tags) | auth-service |
|---|---|
| ![Account](docs/images/dockerhub-account-service.png) | ![Auth](docs/images/dockerhub-auth-service.png) |

| balance-service | transaction-service |
|---|---|
| ![Balance](docs/images/dockerhub-balance-service.png) | ![Transaction](docs/images/dockerhub-transaction-service.png) |

![Frontend](docs/images/dockerhub-frontend.png)

---

### GitOps — ArgoCD

**12 applications — all Healthy and Synced:**

![ArgoCD Apps Page 1](docs/images/argocd-apps-1.png)

![ArgoCD Apps Page 2](docs/images/argocd-apps-2.png)

---

### Monitoring — Grafana & Prometheus

**Custom banking metrics dashboard — login attempts, transaction volume, account operations, DB errors:**

![Grafana Service Metrics Top](docs/images/grafana-service-metrics-top.png)

![Grafana Service Metrics Bottom](docs/images/grafana-service-metrics-bottom.png)

**Node Exporter — EKS node CPU, memory, disk:**

![Grafana Node Exporter](docs/images/grafana-node-exporter.png)

**Prometheus targets — all 4 bankapp service monitors up:**

![Prometheus Targets](docs/images/prometheus-targets.png)

---

### AWS Infrastructure

| ACM Certificate (Issued) | Route53 Hosted Zone |
|---|---|
| ![ACM](docs/images/acm-certificate.png) | ![Route53](docs/images/route53-records.png) |

---

### Kubernetes Cluster

**All pods running across 2 EKS nodes, HPA active:**

![kubectl get all](docs/images/kubectl-get-all.png)

![kubectl get pods wide](docs/images/kubectl-get-pods-wide.png)

![kubectl get ingress](docs/images/kubectl-get-ingress.png)

---

### Database — AWS RDS PostgreSQL

**Schema and live data after load test:**

![RDS Schema](docs/images/rds-schema.png)

| Users Table | Accounts Table |
|---|---|
| ![Users](docs/images/rds-users-table.png) | ![Accounts](docs/images/rds-accounts-table.png) |

![Transactions Table](docs/images/rds-transactions-table.png)

---

## Tech Stack

| Layer          | Technology                                                                      |
|----------------|---------------------------------------------------------------------------------|
| Frontend       | React 18, Vite, Axios, Nginx                                                    |
| Backend        | Python 3.12, FastAPI, Uvicorn                                                   |
| Database       | PostgreSQL 16 (AWS RDS)                                                         |
| Auth           | JWT HS256, bcrypt password hashing                                              |
| Containers     | Docker (multi-stage builds, non-root user)                                      |
| Orchestration  | Kubernetes (AWS EKS)                                                            |
| CI             | Jenkins + [Shared Library](https://github.com/kishor-95/bankapp-shared.git) (Groovy) |
| CD             | ArgoCD (GitOps, App of Apps, auto-sync)                                         |
| Registry       | Docker Hub                                                                      |
| IaC            | Terraform (EKS, RDS, VPC, ALB Controller)                                       |
| Monitoring     | Prometheus + Grafana + Alertmanager (kube-prometheus-stack), prometheus_client  |
| Autoscaling    | Kubernetes HPA + Metrics Server                                                 |
| Load Testing   | k6                                                                              |
| Security       | Trivy image scan, pip-audit, SonarQube, JWT secrets                             |

---

## Repository Structure

```
banking-microservices-devops/
│
├── auth-service/                   # FastAPI — login, register, JWT verify
│   ├── main.py
│   ├── metrics.py                  # Prometheus custom metrics
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│       ├── conftest.py
│       ├── test_auth_service.py
│       └── test_metrics.py
│
├── account-service/                # FastAPI — account management
│   ├── main.py
│   ├── metrics.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│
├── balance-service/                # FastAPI — balance queries
│   ├── main.py
│   ├── metrics.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│
├── transaction-service/            # FastAPI — deposit, withdraw, history
│   ├── main.py
│   ├── metrics.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│
├── frontend/                       # React 18 + Vite served by Nginx
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── context/
│   │   └── pages/
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── __tests__/
│
├── helm/                           # Helm chart (alternative to raw manifests)
│   └── bankapp/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-production.yaml
│       └── templates/
│
├── kubernetes/                     # GitOps source of truth — ArgoCD watches this
│   ├── .argocdignore               # Excludes secrets/ and argocd/ from sync
│   ├── argocd/                     # App of Apps manifests
│   │   ├── project.yaml            # ArgoCD Project with Secret blacklist
│   │   ├── app-of-apps.yaml        # Root app — manages all 11 child apps
│   │   └── apps/
│   │       ├── namespace-app.yaml
│   │       ├── configmaps-app.yaml
│   │       ├── db-init-job-app.yaml
│   │       ├── account-service-app.yaml
│   │       ├── auth-service-app.yaml
│   │       ├── balance-service-app.yaml
│   │       ├── transaction-service-app.yaml
│   │       ├── frontend-app.yaml
│   │       ├── hpa-app.yaml
│   │       ├── ingress-app.yaml
│   │       └── monitoring-app.yaml
│   ├── namespace/
│   ├── secrets/                    # Ignored by ArgoCD — bootstrapped manually
│   ├── configmaps/
│   ├── db-init-job/
│   ├── auth-service/
│   ├── account-service/
│   ├── balance-service/
│   ├── transaction-service/
│   ├── frontend/
│   ├── hpa/
│   ├── ingress/
│   └── monitoring/
│       ├── bank_dashboard.json     # Grafana dashboard — import via UI
│       ├── prometheusrule-bankapp.yaml
│       ├── networkpolicy-backend-restrict.yaml
│       ├── servicemonitor-account.yaml
│       ├── servicemonitor-auth.yaml
│       ├── servicemonitor-balance.yaml
│       └── servicemonitor-transaction.yaml
│
├── prometheus/
│   └── prometheus.yml              # Prometheus config for local docker-compose
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
├── docs/
│   └── images/                     # README screenshots
│
├── db/
│   └── init.sql                    # PostgreSQL schema — run once via K8s Job
│
├── docker-compose.yml              # Local development only
└── .env.example

# Jenkins Shared Library (separate repo)
# https://github.com/kishor-95/bankapp-shared.git
```

---

## End-to-End Flow

```
Developer pushes code to feature branch
              │
              ▼
     Jenkins picks up build
              │
    ┌─────────┴──────────┐
    │  Checkout           │  1s
    │  Lint (flake8)      │  5s
    │  Test (pytest)      │  17-20s
    │  SonarQube          │  12-15s
    │  Docker Build       │  17s
    │  Trivy Scan         │  3-4s   ← fails on CRIT/HIGH CVE
    │  Docker Push        │  13s
    │  Update Manifests   │  3s     ← yq patches image tag in Git
    └─────────────────────┘
              │
    git push to main (image tag updated)
              │
              ▼
    ArgoCD detects diff (polls every 3 min)
              │
              ▼
    Rolling update on EKS — zero downtime
              │
              ▼
    User accesses https://techpluse.online ✅
```

---

## CI/CD Pipeline

The entire pipeline logic lives in a reusable Jenkins Shared Library — nothing is duplicated across services.

> 📦 **Shared Library:**  [vaultx-shared-lib](https://github.com/kishor-95/bankapp-shared.git)

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

All CI logic (lint, test, SonarQube, Docker build, Trivy scan, push, GitOps update) lives in the shared library.

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

| Method | Endpoint         | Auth | Description           |
|--------|------------------|------|-----------------------|
| GET    | `/auth/health`   | ❌   | Liveness probe        |
| POST   | `/auth/register` | ❌   | Register + return JWT |
| POST   | `/auth/login`    | ❌   | Login + return JWT    |
| GET    | `/auth/verify`   | ✅   | Validate Bearer token |

### Account Service — `/accounts`

| Method | Endpoint                 | Auth | Description          |
|--------|--------------------------|------|----------------------|
| GET    | `/accounts/health`       | ❌   | Liveness probe       |
| GET    | `/accounts/me`           | ✅   | List my accounts     |
| GET    | `/accounts/profile`      | ✅   | My user profile      |
| POST   | `/accounts`              | ✅   | Open new account     |
| DELETE | `/accounts/{account_id}` | ✅   | Close account (soft) |

### Balance Service — `/balance`

| Method | Endpoint                | Auth | Description            |
|--------|-------------------------|------|------------------------|
| GET    | `/balance/health`       | ❌   | Liveness probe         |
| GET    | `/balance`              | ✅   | All my balances        |
| GET    | `/balance/{account_id}` | ✅   | Single account balance |

### Transaction Service — `/transactions`

| Method | Endpoint                     | Auth | Description         |
|--------|------------------------------|------|---------------------|
| GET    | `/transactions/health`       | ❌   | Liveness probe      |
| POST   | `/transactions/deposit`      | ✅   | Deposit funds       |
| POST   | `/transactions/withdraw`     | ✅   | Withdraw funds      |
| GET    | `/transactions/{account_id}` | ✅   | Transaction history |

---

## Environment Variables

| Variable           | Source    | Description                                 |
|--------------------|-----------|---------------------------------------------|
| `DB_HOST`          | ConfigMap | RDS endpoint — update after terraform apply |
| `DB_PORT`          | ConfigMap | 5432                                        |
| `JWT_EXPIRE_HOURS` | ConfigMap | Token expiry in hours (default: 24)         |
| `DB_NAME`          | Secret    | Database name                               |
| `DB_USER`          | Secret    | Database username                           |
| `DB_PASSWORD`      | Secret    | Database password                           |
| `JWT_SECRET`       | Secret    | Signing key — minimum 64 chars in prod      |

---

## Local Development

```bash
cp .env.example .env
# Edit .env with your values
docker compose up --build

# App:                  http://localhost:80
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

# Account / Balance / Transaction service
cd account-service && pytest tests/ -v --cov=.
cd balance-service && pytest tests/ -v --cov=.
cd transaction-service && pytest tests/ -v --cov=.
```

Tests use `unittest.mock` — no database or external services required.

---
## Jenkins Setup
For full Jenkins setup instructions see [Jenkins Setup Guide](docs/jenkins-setup.md).

---

## Infrastructure — Terraform

```bash
cd Terraform/environments/dev

terraform init
terraform plan
terraform apply        # ~15 minutes

# Configure kubectl
aws eks update-kubeconfig \
  --region ap-south-1 \
  --name $(terraform output -raw eks_cluster_name)

kubectl get nodes      # should show 2 nodes Ready
```

**What gets created:**

| Resource        | Details                               |
|-----------------|---------------------------------------|
| VPC             | Public + private subnets, NAT Gateway |
| EKS Cluster     | Managed node group, 2 nodes           |
| RDS PostgreSQL  | Private subnet, encrypted at rest     |
| ALB Controller  | Helm-installed, IRSA-enabled          |
| Security Groups | Least-privilege between EKS and RDS   |

> After `terraform apply`, copy the RDS endpoint from the output and update `DB_HOST` in `kubernetes/configmaps/configmaps.yaml`, then push to Git before deploying.

---

## Domain, DNS and HTTPS

### Domain Setup (GoDaddy + Route53)

```
1. Purchase domain from GoDaddy
2. Create Route53 Hosted Zone → note the 4 AWS nameservers
3. Update GoDaddy nameservers:
   GoDaddy → DNS → Nameservers → Enter Custom Nameservers
   → paste all 4 AWS nameservers WITHOUT trailing dot
     e.g. ns-1009.awsdns-62.net  (not ns-1009.awsdns-62.net.)
4. Wait for propagation (~30 min to 2 hours)
   Check: https://dnschecker.org → your domain → NS
```

### Route53 Records

```
Route53 → Hosted Zones → yourdomain.com → Create Record

Record 1 — root domain:
  Name:     (leave empty)
  Type:     A
  Alias:    ON
  Target:   Alias to Application and Classic Load Balancer
  Region:   ap-south-1
  LB:       select your ALB from dropdown

Record 2 — www:
  Name:     www
  Type:     A
  Alias:    ON
  Target:   same ALB as above
```

### ACM Certificate (HTTPS)

```
AWS Console → Certificate Manager → ap-south-1 → Request certificate
  Domain names:
    yourdomain.com
    *.yourdomain.com
  Validation: DNS validation
  → Request

Then: ACM → your cert → Create records in Route53 (one click)
Wait 2-5 minutes for status: Issued ✅
```

### Ingress with HTTPS

```yaml
annotations:
  alb.ingress.kubernetes.io/scheme: internet-facing
  alb.ingress.kubernetes.io/target-type: ip
  alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
  alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:REGION:ACCOUNT:certificate/ID
  alb.ingress.kubernetes.io/ssl-redirect: "443"
  alb.ingress.kubernetes.io/healthcheck-path: /health
```

Push to Git → ArgoCD syncs → HTTPS live ✅

---

## Kubernetes Deployment

Two methods supported. **Method 2 (ArgoCD) is recommended.**

### Method 1 — Manual kubectl

```bash
# 1. Namespace
kubectl apply -f kubernetes/namespace/namespace.yaml

# 2. Secrets and ConfigMaps
kubectl apply -f kubernetes/secrets/secrets.yaml
kubectl apply -f kubernetes/configmaps/

# 3. Init database schema
kubectl apply -f kubernetes/db-init-job/db-init-job.yaml
kubectl wait --for=condition=complete job/db-init-job -n bankapp --timeout=120s

# 4. Services
kubectl apply -f kubernetes/auth-service/
kubectl apply -f kubernetes/account-service/
kubectl apply -f kubernetes/balance-service/
kubectl apply -f kubernetes/transaction-service/
kubectl apply -f kubernetes/frontend/

# 5. HPA + Ingress
kubectl apply -f kubernetes/hpa/
kubectl apply -f kubernetes/ingress/ingress.yaml

# 6. Monitoring
kubectl apply -f kubernetes/monitoring/

# 7. Verify
kubectl get pods -n bankapp
kubectl get ingress -n bankapp
```

### Method 2 — ArgoCD GitOps (Recommended)

#### Secret protection — 3 layers

| Layer | Mechanism | Effect |
|---|---|---|
| 1 | `.argocdignore` | Skips `secrets/` folder at file level |
| 2 | `directory.exclude` in Application | Source-level exclusion |
| 3 | `namespaceResourceBlacklist` in Project | Hard block — refuses to sync `Secret` kind |

#### Step 1 — Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl patch svc argocd-server -n argocd \
  -p '{"spec": {"type": "LoadBalancer"}}'

## OR

kubectl port-forward -n argocd service/argocd-server 8080:443     ## local access 

kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

#### Step 2 — Connect Git repo for private repo

```bash
argocd login <ARGOCD_SERVER_URL>

argocd repo add https://github.com/kishor-95/banking-microservices-devops.git \
  --username <github-username> \
  --password <github-token>
```

#### Step 3 — Bootstrap secrets (one-time only)

```bash
kubectl create namespace bankapp --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic bankapp-backend-secret \
  --namespace=bankapp \
  --from-literal=DB_NAME="bankapp" \
  --from-literal=DB_USER="<rds-username>" \
  --from-literal=DB_PASSWORD="<rds-password>" \
  --from-literal=JWT_SECRET="$(openssl rand -base64 64)" \
  --dry-run=client -o yaml | kubectl apply -f -

# OR — update the existing secrets.yaml and apply it directly
kubectl apply -f kubernetes/secrets/secrets.yaml -n bankapp
```

#### Step 4 — Apply Project and root App

```bash
kubectl apply -f kubernetes/argocd/project.yaml
kubectl apply -f kubernetes/argocd/app-of-apps.yaml
```

#### Sync wave order

| Wave | App | Why |
|------|-----|-----|
| -1 | namespace | Must exist before everything else |
| 0  | configmaps | Pods need config before starting |
| 1  | db-init-job | Schema before services connect |
| 2  | account / auth / balance / transaction | Backend (parallel) |
| 3  | frontend | After backends ready |
| 4  | hpa, ingress | Autoscaling + routing last |
| 5  | monitoring | Observability after all services up |

#### Useful commands

```bash
argocd app list
argocd app get bankapp-account-service
argocd app sync bankapp-root
argocd app diff bankapp-frontend
argocd app history bankapp-auth-service
argocd app rollback bankapp-auth-service <revision>
argocd app refresh bankapp-root --hard
```

---

## Monitoring

### Installation
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

# Wait for all pods Running
kubectl get pods -n monitoring

# Apply bankapp monitoring objects
kubectl apply -f kubernetes/monitoring/servicemonitor-auth.yaml
kubectl apply -f kubernetes/monitoring/servicemonitor-account.yaml
kubectl apply -f kubernetes/monitoring/servicemonitor-balance.yaml
kubectl apply -f kubernetes/monitoring/servicemonitor-transaction.yaml
kubectl apply -f kubernetes/monitoring/prometheusrule-bankapp.yaml
kubectl apply -f kubernetes/monitoring/networkpolicy-backend-restrict.yaml
```

### Access Grafana

```bash
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring

# http://localhost:3000

kubectl get secret kube-prometheus-stack-grafana -n monitoring \
  -o jsonpath='{.data.admin-password}' | base64 -d; echo
```

### Import the Custom Dashboard

```
Grafana → Dashboards → Import
→ Upload dashboard JSON file
→ Select kubernetes/monitoring/bank_dashboard.json
→ Select Prometheus datasource
→ Import ✅
```

### Access Prometheus

```bash
kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring

# http://localhost:9090/targets — all 4 bankapp service monitors show up ✅
```

### Custom Metrics per Service

| Service             | Metrics |
|---------------------|---------|
| auth-service        | login attempts by status, registrations by status |
| account-service     | accounts created by type, operations by outcome |
| balance-service     | balance queries by outcome |
| transaction-service | transaction volume, errors by type, processed by type/status |

### Alerts

| Alert | Severity | Condition |
|---|---|---|
| BankAppServiceDown | critical | `up == 0` for 1 min |
| BankAppHighErrorRate | warning | 5xx rate > 5% for 2 min |
| BankAppHighLoginFailureRate | warning | > 5 failed logins/sec for 2 min |
| BankAppHighLatency | warning | P95 > 1s for 5 min |
| BankAppPodRestarting | warning | > 3 restarts in 15 min |
| BankAppDBConnectionErrors | critical | Any DB error in 5 min window |

---

## Autoscaling

HPA requires Metrics Server to read CPU usage. Install it once before applying HPA manifests:

```bash
# Install Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify — TARGETS must show real percentages, not <unknown>
kubectl get hpa -n bankapp
```

| Service             | CPU Target | Min | Max |
|---------------------|------------|-----|-----|
| auth-service        | 60%        | 2   | 8   |
| account-service     | 70%        | 2   | 6   |
| balance-service     | 70%        | 2   | 6   |
| transaction-service | 70%        | 2   | 6   |

---

## Generating JWT Secret

```bash
kubectl create secret generic bankapp-backend-secret \
  --from-literal=JWT_SECRET="$(openssl rand -base64 64)" \
  --from-literal=DB_NAME="bankapp" \
  --from-literal=DB_USER="postgres" \
  --from-literal=DB_PASSWORD="your-rds-password" \
  -n bankapp \
  --dry-run=client -o yaml | kubectl apply -f -

# OR — update the existing secrets.yaml and apply it directly
kubectl apply -f kubernetes/secrets/secrets.yaml -n bankapp
```

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
argocd app diff bankapp-<service>
argocd app sync bankapp-<service>
argocd app refresh bankapp-root --hard

# Prometheus not scraping
kubectl get servicemonitor -n monitoring
kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring
# localhost:9090/targets — check all bankapp monitors show 2/2 up

# DB connectivity from inside a pod
kubectl exec -it <pod-name> -n bankapp -- \
  python -c "import psycopg2; print('DB ok')"
```

---

## Key Design Decisions

**Stateless services** — JWT validated locally in each service using the shared `JWT_SECRET`. Safe to run multiple replicas with zero-downtime rolling deploys.

**Row-level locking** — `transaction-service` uses `SELECT ... FOR UPDATE`. Prevents double-spend race conditions across concurrent replicas.

**Append-only ledger** — `transactions` table is never updated or deleted. Balance stored in `accounts.balance`, updated atomically in the same DB transaction.

**Non-root containers** — all Dockerfiles run as a non-root user. Required for most production Kubernetes security policies.

**GitOps single source of truth** — `kubernetes/` is the only deploy mechanism. ArgoCD reverts any out-of-band changes automatically (`selfHeal: true`). Secrets are the only exception — applied once via bootstrap script and protected by a Project-level blacklist.

**App of Apps pattern** — each Kubernetes folder is its own ArgoCD Application. Per-service sync status, independent rollback, clear ownership boundaries.

**Security scanning in CI** — Trivy blocks CRIT/HIGH CVEs before any image reaches the registry. pip-audit blocks known vulnerable Python dependencies at install time.

---

## Teardown

> ⚠️ **Order matters** — delete the Ingress first so the ALB Controller removes the AWS ALB. If you run `terraform destroy` before deleting the Ingress, Terraform cannot delete the VPC because the ALB still exists inside it, leaving orphaned AWS resources.

```bash
# Step 1 — Delete Ingress (ALB Controller removes ALB from AWS)
kubectl delete ingress bankapp-frontend-ingress -n bankapp

# Step 2 — Wait for ALB to be fully deleted (~30-60 seconds)
# Verify in AWS Console → EC2 → Load Balancers

# Step 3 — Delete ArgoCD root app (prevents ingress being recreated)
kubectl delete application bankapp-root -n argocd

# Step 4 — Destroy all infrastructure
cd Terraform/environments/dev
terraform destroy
# Type "yes" — removes EKS, RDS, VPC, Security Groups (~15 minutes)
```

> 💸 EKS + RDS + ALB running 24/7 costs ~$5-10/day — always destroy after demo.