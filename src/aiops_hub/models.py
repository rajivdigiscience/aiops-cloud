from typing import Any, Literal

from pydantic import BaseModel, Field

ProviderName = Literal["aws", "azure", "gcp"]
TaskCategory = Literal["L1", "L2"]
RoleName = Literal["viewer", "operator", "admin"]


class TaskDefinition(BaseModel):
    name: str
    description: str
    category: TaskCategory
    required_params: list[str] = Field(default_factory=list)


class TaskExecutionRequest(BaseModel):
    provider: ProviderName
    task: str
    resource_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class TaskExecutionResponse(BaseModel):
    provider: ProviderName
    task: str
    status: Literal["success", "failed", "pending_approval"]
    output: dict[str, Any] = Field(default_factory=dict)
    remediation: list[str] = Field(default_factory=list)
    approval_id: str | None = None


class IncidentTriageRequest(BaseModel):
    provider: ProviderName
    title: str
    description: str
    logs: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentTriageResponse(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    suspected_causes: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    summary: str


class ProviderCommandResult(BaseModel):
    ok: bool
    command: list[str]
    raw_output: str | None = None
    parsed: Any | None = None
    error: str | None = None


class AuthContext(BaseModel):
    role: RoleName
    key_fingerprint: str


class ApprovalRequest(BaseModel):
    id: str
    provider: ProviderName
    task: str
    resource_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    requested_by_role: RoleName
    requested_by_key_fingerprint: str
    reason: str
    status: Literal["pending", "approved", "rejected"]
    review_note: str | None = None
    reviewer_role: RoleName | None = None
    reviewer_key_fingerprint: str | None = None
    created_at: str
    reviewed_at: str | None = None


class ApprovalReviewRequest(BaseModel):
    approve: bool
    note: str = ""
    execute_on_approve: bool = True


class ApprovalReviewResponse(BaseModel):
    approval: ApprovalRequest
    execution_result: TaskExecutionResponse | None = None


class AuditLogEntry(BaseModel):
    id: int
    timestamp: str
    actor_role: RoleName
    actor_key_fingerprint: str
    action: str
    provider: ProviderName | None = None
    task: str | None = None
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
