from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from aiops_hub.auth import require_auth, require_min_role
from aiops_hub.config import get_settings
from aiops_hub.exceptions import TaskNotFoundError
from aiops_hub.models import (
    ApprovalReviewRequest,
    ApprovalReviewResponse,
    AuditLogEntry,
    AuthContext,
    IncidentTriageRequest,
    IncidentTriageResponse,
    TaskExecutionRequest,
    TaskExecutionResponse,
)
from aiops_hub.service import AIOpsService

settings = get_settings()
service = AIOpsService()

app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins() or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


@app.get("/providers")
def providers(auth: AuthContext = Depends(require_auth)) -> dict[str, list[str]]:
    require_min_role(auth, "viewer")
    return {"providers": service.list_providers()}


@app.get("/tasks")
def tasks(auth: AuthContext = Depends(require_auth)):
    require_min_role(auth, "viewer")
    return {"tasks": [t.model_dump() for t in service.list_tasks()]}


@app.post("/tasks/execute", response_model=TaskExecutionResponse)
def execute_task(request: TaskExecutionRequest, auth: AuthContext = Depends(require_auth)):
    require_min_role(auth, "operator")
    try:
        return service.execute_task_with_controls(request, auth)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/incidents/triage", response_model=IncidentTriageResponse)
def triage(request: IncidentTriageRequest, auth: AuthContext = Depends(require_auth)):
    require_min_role(auth, "operator")
    return service.triage_incident(request, auth)


@app.get("/approvals")
def list_approvals(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    auth: AuthContext = Depends(require_auth),
):
    require_min_role(auth, "operator")
    return {"approvals": [approval.model_dump() for approval in service.list_approvals(status=status, limit=limit)]}


@app.post("/approvals/{approval_id}/review", response_model=ApprovalReviewResponse)
def review_approval(
    approval_id: str,
    request: ApprovalReviewRequest,
    auth: AuthContext = Depends(require_auth),
):
    require_min_role(auth, "admin")
    try:
        return service.review_approval(
            approval_id,
            approve=request.approve,
            note=request.note,
            execute_on_approve=request.execute_on_approve,
            reviewer=auth,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/audit/logs", response_model=list[AuditLogEntry])
def audit_logs(
    limit: int = Query(default=200, ge=1, le=1000),
    action: str | None = Query(default=None),
    status: str | None = Query(default=None),
    auth: AuthContext = Depends(require_auth),
):
    require_min_role(auth, "operator")
    return service.list_audit(limit=limit, action=action, status=status)
