# CI Setup — BankApp Microservices

## Stack Overview

| Component | Tool | Version |
|---|---|---|
| CI Server | Jenkins | 2.555.3 |
| Code Quality | SonarQube | Community |
| Shared Library | `vaultx-shared-lib` | `bankapp-shared@main` |
| Container Runtime | Docker | Latest |
| Source Control | GitHub | `kishor-95/banking-microservices-devops` |

---

## Jenkins Server

**URL:** `http://<IP>:8080`

**Installed on:** Ubuntu (AWS EC2 )

### Required Plugins

| Plugin | Purpose |
|---|---|
| Pipeline | Core pipeline execution |
| Pipeline: Shared Groovy Libraries | Loads `vaultx-shared-lib@main` |
| Git | SCM checkout |
| GitHub | Webhook integration |
| Docker Pipeline | Docker build/push in pipeline |
| SonarQube Scanner | Code quality analysis |
| Workspace Cleanup | `cleanWs()` stage |
| JUnit | Test result publishing |
| HTML Publisher | Coverage report publishing |
| Build Timeout | Prevent stuck builds |
| AnsiColor | Colored console output |

### Global Credentials

| ID | Kind | Used For |
|---|---|---|
| `git-creds` | Username + Password (PAT) | GitHub checkout |
| `docker-creds` | Username + Password | DockerHub push |
| `sonar-token` | Secret Text | SonarQube analysis |

### Shared Library Configuration

**Path:** Manage Jenkins → System → Global Pipeline Libraries

| Field | Value |
|---|---|
| Name | `vaultx-shared-lib` |
| Default Version | `main` |
| Repository | `https://github.com/kishor-95/bankapp-shared.git` |
| Credentials | `git-creds` |

### SonarQube Server Configuration

**Path:** Manage Jenkins → System → SonarQube Servers

| Field | Value |
|---|---|
| Name | `SonarQube` |
| URL | `http://<IP>:9000` |
| Auth Token | `sonar-token` |

### SonarQube Scanner Tool

**Path:** Manage Jenkins → Tools → SonarQube Scanner

| Field | Value |
|---|---|
| Name | `sonar-scanner` |
| Install Automatically | Yes |

---

## SonarQube Server

**URL:** `http://<IP>:9000`

**Running via Docker:**

```bash
docker run -d \
  --name sonarqube \
  -p 9000:9000 \
  -v sonarqube_data:/opt/sonarqube/data \
  -v sonarqube_logs:/opt/sonarqube/logs \
  -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true \
  sonarqube:community
```

### SonarQube Projects

| Project Key | Service | Coverage Threshold |
|---|---|---|
| `vaultx-account-service` | account-service | 80% |
| `vaultx-auth-service` | auth-service | 85% |
| `vaultx-balance-service` | balance-service | 80% |
| `vaultx-transaction-service` | transaction-service | 82% |
| `bankapp-frontend` | frontend | N/A |

### Quality Gate Configuration

Default gate "Sonar Way" is used with one modification — the **New Issues** condition
is set to allow informational issues. Only the following conditions will fail the gate:

- Coverage on New Code **< 80%**
- New Bugs **> 0**
- New Vulnerabilities **> 0**
- Duplicated Lines **> 3%**

---

## Jenkins Pipelines

Each service has a dedicated pipeline job:

| Job Name | Jenkinsfile Path | Branch |
|---|---|---|
| `account-service` | `account-service/Jenkinsfile` | `main` |
| `auth-service` | `auth-service/Jenkinsfile` | `main` |
| `balance-service` | `balance-service/Jenkinsfile` | `main` |
| `transaction-service` | `transaction-service/Jenkinsfile` | `main` |
| `Frontend-service` | `frontend/Jenkinsfile` | `main` |

### Pipeline Stages (Python Services)

```
Checkout → Lint + Test + Dependency Scan (parallel) → SonarQube → Docker Build → Push
```

| Stage | Tool | Failure Condition |
|---|---|---|
| Checkout | Git | Branch not found |
| Lint | flake8 7.0.0 (Docker) | Any PEP8 violation |
| Test | pytest + pytest-cov (Docker) | Any test failure or coverage below threshold |
| Dependency Scan | pip-audit (Docker) | Critical vulnerabilities found |
| SonarQube | sonar-scanner | Quality Gate ERROR |
| Docker Build | docker build | Build failure |
| Push | DockerHub | Auth failure |

### Pipeline Stages (Frontend)

```
Checkout → Build → Test → Dependency Scan → SonarQube → Docker Build → Push
```

| Stage | Tool | Notes |
|---|---|---|
| Build | node:20-alpine + Vite | Output: `dist/` |
| Test | Vitest + coverage-v8 | 55 tests |
| Dependency Scan | npm audit | Fails on critical vulnerabilities only |

---

## GitHub Webhooks

Webhooks allow GitHub to automatically trigger Jenkins builds on every push.

### How to Add a Webhook

**1.** Go to your GitHub repository:
`https://github.com/kishor-95/banking-microservices-devops`

**2.** Navigate to: **Settings → Webhooks → Add webhook**

**3.** Fill in the form:

| Field | Value |
|---|---|
| Payload URL | `http://<IP>:8080/github-webhook/` |
| Content type | `application/json` |
| Secret | *(leave blank)* |
| Which events | **Just the push event** |
| Active | ✅ checked |

**4.** Click **Add webhook**

> ⚠️ The trailing slash in `/github-webhook/` is required. Without it the webhook returns 404.

### Enable Webhook Trigger in Each Jenkins Job

For each pipeline job:

1. Open the job → **Configure**
2. Scroll to **Build Triggers**
3. Check **GitHub hook trigger for GITScm polling**
4. Save

### Verify the Webhook is Working

After adding, GitHub shows delivery history under:
**Settings → Webhooks → click your webhook → Recent Deliveries**

A green tick means Jenkins received and processed the payload.
A red X means delivery failed — check the Response tab for the error.

### Webhook Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 404 response | Missing trailing slash in URL | Add `/` at end of URL |
| 400 Invalid JSON | Empty POST body (e.g. manual curl test) | Normal — only fails for empty payloads, not real pushes |
| Connection refused | Port 8080 blocked | `sudo ufw allow 8080` or add inbound rule in AWS Security Group |
| Build not triggered | Trigger not enabled in job | Enable "GitHub hook trigger for GITScm polling" |
| Webhook fires but wrong job | Multiple jobs on same repo | Each job watches its own Jenkinsfile path |

### Test the Webhook Manually

Push a commit to the `main` branch:

```bash
git commit --allow-empty -m "test: trigger webhook"
git push origin main
```

Check Jenkins dashboard — the relevant pipeline should start within a few seconds.

---

## AWS Security Group Rules

The EC2 instance running Jenkins + SonarQube needs these inbound rules:

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | Your IP | SSH access |
| 8080 | TCP | 0.0.0.0/0 | Jenkins UI + webhook endpoint |
| 9000 | TCP | 0.0.0.0/0 | SonarQube UI |

> For production, restrict port 8080 and 9000 to specific IPs rather than 0.0.0.0/0.

---

## Common Issues and Fixes

| Error | Fix |
|---|---|
| `No tool named sonar-scanner found` | Add SonarQube Scanner in Manage Jenkins → Tools with name `sonar-scanner` |
| `vaultx-shared-lib not found` | Check Global Pipeline Libraries — name must be exactly `vaultx-shared-lib` |
| `Security not defined` in FastAPI | Add `Security` to FastAPI imports: `from fastapi import ..., Security` |
| `docker: permission denied` | Run `sudo usermod -aG docker jenkins && sudo systemctl restart jenkins` |
| Quality Gate stuck on PENDING | Add webhook in SonarQube: Administration → Webhooks → `http://<jenkins>:8080/sonarqube-webhook/` |
| Quality Gate ERROR — New Issues | Go to SonarQube → Issues → New Code tab to see the specific issue |
| `W291 trailing whitespace` | Remove trailing spaces from the flagged line |
| `W292 no newline at end of file` | Add a blank line at end of file |
| `F841 local variable assigned but never used` | Remove the variable assignment or use `return` directly |
| `assert 403 == 401` | `HTTPBearer(auto_error=False)` + `if credentials is None: raise HTTPException(401)` |

---

## SonarQube Webhook (Jenkins ↔ SonarQube)

This is separate from GitHub webhooks. It lets SonarQube notify Jenkins when
analysis is complete so `waitForQualityGate()` doesn't time out.

**Path:** SonarQube → Administration → Configuration → Webhooks → Create

| Field | Value |
|---|---|
| Name | `Jenkins` |
| URL | `http://<IP>:8080/sonarqube-webhook/` |
| Secret | *(leave blank)* |

> Both webhooks must be configured — the GitHub one triggers builds, the SonarQube
> one completes the Quality Gate check inside the build.