from typing import Callable

from aiops_hub.exceptions import TaskNotFoundError
from aiops_hub.models import TaskDefinition, TaskExecutionRequest, TaskExecutionResponse
from aiops_hub.providers.base import CloudProvider

TASKS: dict[str, TaskDefinition] = {
    "check_instance_status": TaskDefinition(
        name="check_instance_status",
        description="Check VM/instance health and runtime status",
        category="L1",
        required_params=["resource_id"],
    ),
    "check_storage_health": TaskDefinition(
        name="check_storage_health",
        description="Inspect cloud storage or disk health",
        category="L1",
        required_params=[],
    ),
    "check_network_health": TaskDefinition(
        name="check_network_health",
        description="Inspect NIC/network status",
        category="L1",
        required_params=[],
    ),
    "list_recent_events": TaskDefinition(
        name="list_recent_events",
        description="Fetch recent control-plane events",
        category="L1",
        required_params=[],
    ),
    "restart_instance": TaskDefinition(
        name="restart_instance",
        description="Restart a VM/instance for recovery",
        category="L2",
        required_params=["resource_id"],
    ),
    "diagnostic_bundle": TaskDefinition(
        name="diagnostic_bundle",
        description="Collect status + network + events in one call",
        category="L2",
        required_params=[],
    ),
}


def list_tasks() -> list[TaskDefinition]:
    return list(TASKS.values())


def get_task_definition(task_name: str) -> TaskDefinition:
    definition = TASKS.get(task_name)
    if not definition:
        raise TaskNotFoundError(f"Unknown task: {task_name}")
    return definition


def _require_resource_id(request: TaskExecutionRequest) -> str:
    if not request.resource_id:
        raise ValueError("resource_id is required for this task")
    return request.resource_id


def execute_task(provider: CloudProvider, request: TaskExecutionRequest) -> TaskExecutionResponse:
    handlers: dict[str, Callable[[], dict]] = {
        "check_instance_status": lambda: provider.check_instance_status(_require_resource_id(request)),
        "check_storage_health": lambda: provider.check_storage_health(request.resource_id),
        "check_network_health": lambda: provider.check_network_health(request.resource_id),
        "list_recent_events": lambda: provider.list_recent_events(
            request.resource_id, int(request.params.get("limit", 10))
        ),
        "restart_instance": lambda: provider.restart_instance(_require_resource_id(request)),
        "diagnostic_bundle": lambda: {
            "instance_status": provider.check_instance_status(request.resource_id)
            if request.resource_id
            else {"skipped": "resource_id not provided"},
            "storage": provider.check_storage_health(request.resource_id),
            "network": provider.check_network_health(request.resource_id),
            "events": provider.list_recent_events(request.resource_id, int(request.params.get("limit", 10))),
        },
    }

    if request.task not in handlers:
        raise TaskNotFoundError(f"Unknown task: {request.task}")

    output = handlers[request.task]()
    ok = _output_success(output)

    return TaskExecutionResponse(
        provider=provider.name,  # type: ignore[arg-type]
        task=request.task,
        status="success" if ok else "failed",
        output=output,
        remediation=_recommended_remediation(request.task, ok),
    )


def _output_success(output: dict) -> bool:
    if "ok" in output:
        return bool(output.get("ok"))
    for value in output.values():
        if isinstance(value, dict) and "ok" in value and not value.get("ok"):
            return False
    return True


def _recommended_remediation(task_name: str, ok: bool) -> list[str]:
    if ok:
        return ["No immediate action required."]

    fallback = [
        "Validate cloud CLI authentication and permissions.",
        "Check resource identifiers and region/subscription/project context.",
        "Escalate to platform/on-call engineer if service is customer-impacting.",
    ]
    task_hints = {
        "check_instance_status": ["Review VM boot logs and agent health.", "Check recent scaling/deploy changes."],
        "restart_instance": ["Confirm restart completed and service recovered.", "If not, trigger failover runbook."],
        "diagnostic_bundle": ["Attach bundle output to incident ticket for L3 escalation."],
    }
    return task_hints.get(task_name, []) + fallback
