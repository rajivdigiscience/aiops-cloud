from aiops_hub.ai_triage import IncidentTriageEngine
from aiops_hub.config import get_settings
from aiops_hub.exceptions import ProviderError
from aiops_hub.models import (
    ApprovalRequest,
    ApprovalReviewResponse,
    AuthContext,
    IncidentTriageRequest,
    IncidentTriageResponse,
    TaskExecutionRequest,
    TaskExecutionResponse,
)
from aiops_hub.registry import get_provider_registry
from aiops_hub.runbooks import execute_task as execute_runbook
from aiops_hub.runbooks import get_task_definition, list_tasks
from aiops_hub.state_store import StateStore


class AIOpsService:
    def __init__(self) -> None:
        self.providers = get_provider_registry()
        self.triage_engine = IncidentTriageEngine()
        self.state_store = StateStore(get_settings().state_db_path)

    def list_providers(self) -> list[str]:
        return list(self.providers.keys())

    def list_tasks(self):
        return list_tasks()

    def execute_task(self, request: TaskExecutionRequest) -> TaskExecutionResponse:
        provider = self.providers.get(request.provider)
        if not provider:
            raise ProviderError(f"Unsupported provider: {request.provider}")
        return execute_runbook(provider, request)

    def execute_task_with_controls(self, request: TaskExecutionRequest, auth: AuthContext) -> TaskExecutionResponse:
        definition = get_task_definition(request.task)

        if auth.role == "viewer":
            raise PermissionError("viewer role cannot execute tasks")

        if definition.category in {"L2", "L3"} and auth.role != "admin":
            approval = self.state_store.create_approval(
                request=request,
                auth=auth,
                reason=f"{definition.category} task requested by non-admin role",
            )
            self.state_store.record_audit(
                auth=auth,
                action="approval.requested",
                status="pending",
                provider=request.provider,
                task=request.task,
                details={"approval_id": approval.id, "category": definition.category},
            )
            return TaskExecutionResponse(
                provider=request.provider,
                task=request.task,
                status="pending_approval",
                output={"message": "Task requires admin approval", "approval_id": approval.id},
                remediation=["Ask an admin to review this approval request."],
                approval_id=approval.id,
            )

        result = self.execute_task(request)
        self.state_store.record_audit(
            auth=auth,
            action="task.executed",
            status=result.status,
            provider=request.provider,
            task=request.task,
            details={"category": definition.category},
        )
        return result

    def triage_incident(self, request: IncidentTriageRequest, auth: AuthContext) -> IncidentTriageResponse:
        result = self.triage_engine.triage(request)
        self.state_store.record_audit(
            auth=auth,
            action="incident.triaged",
            status="success",
            provider=request.provider,
            details={"severity": result.severity, "title": request.title},
        )
        return result

    def list_approvals(self, status: str | None = None, limit: int = 100) -> list[ApprovalRequest]:
        return self.state_store.list_approvals(status=status, limit=limit)

    def review_approval(
        self,
        approval_id: str,
        *,
        approve: bool,
        note: str,
        execute_on_approve: bool,
        reviewer: AuthContext,
    ) -> ApprovalReviewResponse:
        approval = self.state_store.review_approval(
            approval_id=approval_id,
            approve=approve,
            note=note,
            reviewer=reviewer,
        )

        self.state_store.record_audit(
            auth=reviewer,
            action="approval.reviewed",
            status=approval.status,
            provider=approval.provider,
            task=approval.task,
            details={"approval_id": approval.id, "execute_on_approve": execute_on_approve},
        )

        execution_result: TaskExecutionResponse | None = None
        if approve and execute_on_approve:
            execution_result = self.execute_task(
                TaskExecutionRequest(
                    provider=approval.provider,
                    task=approval.task,
                    resource_id=approval.resource_id,
                    params=approval.params,
                )
            )
            self.state_store.record_audit(
                auth=reviewer,
                action="task.executed_from_approval",
                status=execution_result.status,
                provider=approval.provider,
                task=approval.task,
                details={"approval_id": approval.id},
            )

        return ApprovalReviewResponse(approval=approval, execution_result=execution_result)

    def list_audit(self, limit: int = 200, action: str | None = None, status: str | None = None):
        return self.state_store.list_audit(limit=limit, action=action, status=status)
