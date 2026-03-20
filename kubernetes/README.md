# BankApp — Kubernetes Deployment Guide

> **Database:** AWS RDS (PostgreSQL 16) — externally managed.

---

## Architecture Overview

```
                        ┌──────────────────────────────────┐
                        │         AWS EKS Cluster          │
                        │          (bankapp ns)            │
                        │                                  │
  Internet              │  ┌──────────┐                    │
──────────────►  Ingress│  │ frontend │ (Nginx + React)    │
  :80 / :443            │  └────┬─────┘                    │
                        │       │ /api/*                   │
                        │  ┌────▼──────────────────────┐   │
                        │  │      Backend Services      │  │
                        │  │  auth      :8001           │  │
                        │  │  account   :8002           │  │
                        │  │  balance   :8003           │  │
                        │  │  transaction :8004         │  │
                        │  └────────────┬───────────────┘  │
                        └───────────────┼──────────────────┘
                                        │
                                        ▼
                          ┌─────────────────────────┐
                          │       AWS RDS           │
                          │  PostgreSQL 16          │
                          │  (privately accessible  │
                          │   via VPC — no public   │
                          │   endpoint)             │
                          └─────────────────────────┘
```

---

## Directory Structure

```
k8s/
├── namespace.yaml                  ← bankapp namespace
├── secrets.yaml                    ← RDS credentials + JWT secret
├── configmap.yaml                  ← DB_HOST (RDS endpoint), DB_PORT
├── ingress.yaml                    ← update with your domain
├── auth-service/
│   ├── deployment.yaml             ← fill your image name
│   └── service.yaml
├── account-service/
│   ├── deployment.yaml             ← fill your image name
│   └── service.yaml
├── balance-service/
│   ├── deployment.yaml             ← fill your image name
│   └── service.yaml
├── transaction-service/
│   ├── deployment.yaml             ← fill your image name
│   └── service.yaml
└── frontend/
    ├── deployment.yaml             ← fill your image name
    ├── nginx-configmap.yaml        ← nginx.conf mounted externally
    └── service.yaml
```

> `k8s/postgres/` is not used — database is managed by AWS RDS.

---

## Before You Deploy

### 1. Provision AWS RDS

- Engine: **PostgreSQL 16**
- Instance: `db.t3.micro` (dev) / `db.t3.medium`+ (prod)
- **Disable** public accessibility — keep it inside the VPC
- Place it in the **same VPC** as your EKS cluster
- Note the endpoint — you'll need it in Step 3

Once RDS is up, connect and run the schema:

```bash
psql -h <rds-endpoint> -U postgres -d bankapp -f db/init.sql
```

---

### 2. Fill in image names

Open each `deployment.yaml` and set the `image:` field:

```yaml
image: <your-ecr-account>.dkr.ecr.<region>.amazonaws.com/auth-service:1.0.0
```

Do this for all 5 services: `auth`, `account`, `balance`, `transaction`, `frontend`.

---

### 3. Fill in `configmap.yaml`

Replace `DB_HOST` with your actual RDS endpoint:

```yaml
data:
  DB_HOST: "bankapp.xxxxxxxx.<region>.rds.amazonaws.com"   # ← your RDS endpoint
  DB_PORT: "5432"
  JWT_EXPIRE_HOURS: "24"
```

---

### 4. Fill in `secrets.yaml`

Encode each value before pasting:

```bash
echo -n "your-rds-db-name"     | base64
echo -n "your-rds-username"    | base64
echo -n "your-rds-password"    | base64
echo -n "your-jwt-secret-min-32-chars" | base64
```

Paste the output into `secrets.yaml`. Never commit real values to Git.

---

### 5. Update `ingress.yaml`

```yaml
rules:
  - host: bankapp.yourdomain.com    # ← your actual domain
```

---

## Deploy — in order

```bash
# 1. Namespace
kubectl apply -f k8s/namespace.yaml

# 2. Secrets + ConfigMap (RDS endpoint lives here)
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# 3. Nginx ConfigMap (mounted externally into frontend container)
kubectl apply -f k8s/frontend/nginx-configmap.yaml -n bankapp

# 4. Backend services
kubectl apply -f k8s/auth-service/
kubectl apply -f k8s/account-service/
kubectl apply -f k8s/balance-service/
kubectl apply -f k8s/transaction-service/

# 5. Frontend
kubectl apply -f k8s/frontend/

# 6. Ingress
kubectl apply -f k8s/ingress.yaml
```

No `kubectl wait` for postgres — RDS is already running before the cluster deploys.

---

## Verify Everything Is Up

```bash
# All pods should be Running
kubectl get pods -n bankapp

# Services
kubectl get svc -n bankapp

# Wait for frontend external IP (LoadBalancer)
kubectl get svc frontend -n bankapp --watch

# Confirm backend pods can reach RDS
kubectl exec -it deploy/auth-service -n bankapp -- \
  python -c "import psycopg2; psycopg2.connect(host='<rds-endpoint>', dbname='bankapp', user='postgres', password='<pass>'); print('RDS OK')"
```

---

## Rolling Update — Zero Downtime

All services use `maxUnavailable: 0` + `maxSurge: 1`. A new pod must pass readiness before the old one is terminated.

```bash
# Update a service image
kubectl set image deployment/auth-service \
  auth-service=<ecr-uri>/auth-service:1.1.0 \
  -n bankapp

# Watch the rollout
kubectl rollout status deployment/auth-service -n bankapp

# Rollback if needed
kubectl rollout undo deployment/auth-service -n bankapp
```

---

## Update Nginx Config Without Rebuilding

nginx.conf is mounted from a ConfigMap — change routing rules without touching the Docker image:

```bash
# Edit k8s/frontend/nginx-configmap.yaml then:
kubectl apply -f k8s/frontend/nginx-configmap.yaml -n bankapp
kubectl rollout restart deployment/frontend -n bankapp
kubectl rollout status deployment/frontend -n bankapp
```

---

## Useful Commands

```bash
# All pods status
kubectl get pods -n bankapp

# Tail logs for a service
kubectl logs -l app=auth-service -n bankapp --tail=50 -f

# Describe a failing pod
kubectl describe pod <pod-name> -n bankapp

# Confirm RDS env vars are injected correctly
kubectl exec -it <pod-name> -n bankapp -- env | grep -E "DB_|JWT_"

# Scale a service
kubectl scale deployment balance-service --replicas=3 -n bankapp

# Check ingress
kubectl get ingress -n bankapp
kubectl describe ingress bankapp-ingress -n bankapp
```

---

## Key Design Decisions

| Decision | Why |
|---|---|
| **AWS RDS instead of in-cluster Postgres** | Managed backups, Multi-AZ failover, automated patching — no ops overhead |
| **RDS in same VPC, no public endpoint** | Traffic never leaves AWS network — security best practice |
| **DB credentials in K8s Secret** | Never hardcoded in manifests or image layers |
| **`DB_HOST` in ConfigMap, not Secret** | Endpoint is not sensitive — easier to update if RDS is replaced |
| **`maxUnavailable: 0`** | Old pod stays alive until new one passes readiness — true zero downtime |
| **`maxSurge: 1`** | One extra pod during rollout — minimal resource spike |
| **`IfNotPresent` pull policy** | No unnecessary registry pulls; set to `Always` in CI/CD if needed |
| **`terminationGracePeriodSeconds: 60` on transaction-service** | Financial operations must complete before pod is killed |
| **nginx.conf as ConfigMap** | Update routing rules without rebuilding the frontend Docker image |

---

## AWS-Specific Checklist

- [ ] RDS instance is in the **same VPC** as EKS node group
- [ ] EKS node security group has **inbound rule on port 5432** from the RDS security group
- [ ] RDS security group allows **inbound 5432 from EKS node security group**
- [ ] RDS has **public accessibility disabled**
- [ ] ECR repositories created for all 5 services
- [ ] EKS nodes have IAM role with **ECR pull permissions** (`AmazonEC2ContainerRegistryReadOnly`)
- [ ] `db/init.sql` has been run against the RDS instance before first deploy