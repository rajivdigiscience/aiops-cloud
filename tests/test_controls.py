from pathlib import Path

from aiops_hub.config import get_settings
from aiops_hub.models import AuthContext, IncidentTriageRequest, TaskExecutionRequest, TaskExecutionResponse
from aiops_hub.service import AIOpsService


def _new_service(tmp_path: Path, monkeypatch) -> AIOpsService:
    monkeypatch.setenv("AIOPS_STATE_DB_PATH", str(tmp_path / "aiops_test.db"))
    get_settings.cache_clear()
    return AIOpsService()


def test_operator_l2_task_creates_approval(tmp_path, monkeypatch):
    service = _new_service(tmp_path, monkeypatch)

    response = service.execute_task_with_controls(
        TaskExecutionRequest(provider="aws", task="restart_instance", resource_id="i-123"),
        AuthContext(role="operator", key_fingerprint="op-001"),
    )

    assert response.status == "pending_approval"
    assert response.approval_id

    approvals = service.list_approvals(status="pending", limit=10)
    assert len(approvals) == 1
    assert approvals[0].id == response.approval_id


def test_operator_l3_task_creates_approval(tmp_path, monkeypatch):
    service = _new_service(tmp_path, monkeypatch)

    response = service.execute_task_with_controls(
        TaskExecutionRequest(provider="aws", task="root_cause_analysis", resource_id="i-rca"),
        AuthContext(role="operator", key_fingerprint="op-004"),
    )

    assert response.status == "pending_approval"
    assert response.approval_id


def test_admin_review_can_execute_approved_task(tmp_path, monkeypatch):
    service = _new_service(tmp_path, monkeypatch)
    pending = service.execute_task_with_controls(
        TaskExecutionRequest(provider="aws", task="restart_instance", resource_id="i-777"),
        AuthContext(role="operator", key_fingerprint="op-002"),
    )

    def _fake_execute(_request: TaskExecutionRequest) -> TaskExecutionResponse:
        return TaskExecutionResponse(
            provider="aws",
            task="restart_instance",
            status="success",
            output={"ok": True, "restarted": "i-777"},
            remediation=["No immediate action required."],
        )

    service.execute_task = _fake_execute  # type: ignore[method-assign]

    review = service.review_approval(
        pending.approval_id or "",
        approve=True,
        note="safe to run",
        execute_on_approve=True,
        reviewer=AuthContext(role="admin", key_fingerprint="adm-001"),
    )

    assert review.approval.status == "approved"
    assert review.execution_result is not None
    assert review.execution_result.status == "success"


def test_triage_writes_audit_log(tmp_path, monkeypatch):
    service = _new_service(tmp_path, monkeypatch)
    _ = service.triage_incident(
        request=IncidentTriageRequest(
            provider="gcp",
            title="Minor warning",
            description="degraded service",
            logs="warning and retry",
        ),
        auth=AuthContext(role="operator", key_fingerprint="op-003"),
    )

    logs = service.list_audit(limit=10, action="incident.triaged")
    assert len(logs) == 1
    assert logs[0].status == "success"
