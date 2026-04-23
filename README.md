# AI Ops Hub (Plug-and-Play Multi-Cloud AI Ops)

AI Ops Hub is a production-oriented starter for cloud operations teams who need one control plane for AWS, Azure, and GCP.

It now includes all three requested tracks:
- Enterprise backend controls: RBAC, approval workflow for L2 actions, and persistent audit logs
- React dashboard: runbooks, incident triage, approvals, and audit view
- Kubernetes Helm chart: deployable package with secrets/config/probes/persistence

## Core capabilities

- Unified runbook API for L1/L2/L3 tasks across cloud providers
- Pluggable provider adapters under `src/aiops_hub/providers`
- AI-assisted incident triage with heuristic fallback and optional OpenAI enrichment
- Role-based access via API keys (`viewer`, `operator`, `admin`)
- L2 guardrail: non-admin L2 actions become approval requests
- Admin review endpoint with optional execute-on-approve
- SQLite-backed audit and approval state

## API surface

- `GET /health`
- `GET /providers`
- `GET /tasks`
- `POST /tasks/execute`
- `POST /incidents/triage`
- `GET /approvals`
- `POST /approvals/{approval_id}/review`
- `GET /audit/logs`

## Engineer activity matrix (L1/L2/L3)

### L1
- `check_instance_status`
- `check_storage_health`
- `check_network_health`
- `list_recent_events`
- `collect_ticket_context`
- `verify_backup_job_status`
- `check_service_error_budget`
- `validate_ssl_certificate_expiry`

### L2
- `restart_instance`
- `diagnostic_bundle`
- `scale_instance_group`
- `isolate_unhealthy_node`
- `flush_stuck_deploy`
- `rotate_service_credentials`

### L3
- `root_cause_analysis`
- `execute_failover_plan`
- `disaster_recovery_drill`
- `security_forensics_workflow`
- `cost_optimization_review`
- `post_incident_review`

## Typical engineering activities by level

- `L1`: alert triage, health checks, ticket enrichment, backup verification, first-response diagnostics.
- `L2`: controlled remediation, targeted recovery actions, deploy rollback/repair, credential rotations.
- `L3`: deep RCA, resilience architecture decisions, failover/disaster workflows, security forensics, preventive design changes.

## Local backend quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
aiops api --host 0.0.0.0 --port 8080
```

Swagger:
- `http://localhost:8080/docs`

## RBAC usage

Default keys in `.env.example`:
- `admin-dev-key`
- `operator-dev-key`
- `viewer-dev-key`

Example request:

```bash
curl -s http://localhost:8080/tasks \
  -H 'X-API-Key: admin-dev-key' | jq
```

Operator attempting L2 action gets approval queue entry:

```bash
curl -s -X POST http://localhost:8080/tasks/execute \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: operator-dev-key' \
  -d '{
    "provider": "aws",
    "task": "restart_instance",
    "resource_id": "i-0123456789abcdef0",
    "params": {}
  }' | jq
```

Admin reviews approval:

```bash
curl -s -X POST http://localhost:8080/approvals/<approval-id>/review \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: admin-dev-key' \
  -d '{"approve": true, "note": "validated", "execute_on_approve": true}' | jq
```

## Dashboard (React)

```bash
cd dashboard
npm install
npm run dev
```

Open:
- `http://localhost:5173`

Dashboard tabs:
- `Runbooks`
- `Incidents`
- `Approvals`
- `Audit`

## Docker

```bash
docker build -t aiops-hub .
docker run --rm -p 8080:8080 --env-file .env aiops-hub
```

Or:

```bash
docker compose up --build
```

## Helm (Kubernetes)

```bash
helm upgrade --install aiops ./helm/aiops-hub \
  --namespace aiops --create-namespace \
  --set image.repository=<your-repo>/aiops-hub \
  --set image.tag=<your-tag> \
  --set keys.admin='<admin-key>' \
  --set keys.operator='<operator-key>' \
  --set keys.viewer='<viewer-key>'
```

Optional persistence:

```bash
helm upgrade --install aiops ./helm/aiops-hub \
  --namespace aiops --create-namespace \
  --set persistence.enabled=true
```

## Tests

```bash
source .venv/bin/activate
pytest -q
```

## Important implementation note

Provider actions currently use vendor CLIs (`aws`, `az`, `gcloud`).
Runtime environments must include those CLIs and cloud identity setup.
