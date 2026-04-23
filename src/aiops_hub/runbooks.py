from typing import Callable

from aiops_hub.exceptions import TaskNotFoundError
from aiops_hub.models import TaskDefinition, TaskExecutionRequest, TaskExecutionResponse
from aiops_hub.providers.base import CloudProvider

TASKS: dict[str, TaskDefinition] = {
    # L1: frontline operations and telemetry checks
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
    "collect_ticket_context": TaskDefinition(
        name="collect_ticket_context",
        description="Collect baseline context for incident/ticket handoff",
        category="L1",
        required_params=[],
    ),
    "verify_backup_job_status": TaskDefinition(
        name="verify_backup_job_status",
        description="Verify backup-related events and last successful run signals",
        category="L1",
        required_params=[],
    ),
    "check_service_error_budget": TaskDefinition(
        name="check_service_error_budget",
        description="Review SLO burn/error budget indicators from telemetry",
        category="L1",
        required_params=[],
    ),
    "validate_ssl_certificate_expiry": TaskDefinition(
        name="validate_ssl_certificate_expiry",
        description="Check certificate expiry risk and renewal lead time",
        category="L1",
        required_params=[],
    ),
    # L2: recovery and controlled remediation
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
    "scale_instance_group": TaskDefinition(
        name="scale_instance_group",
        description="Scale compute group or service target capacity",
        category="L2",
        required_params=[],
    ),
    "isolate_unhealthy_node": TaskDefinition(
        name="isolate_unhealthy_node",
        description="Quarantine problematic node from serving traffic",
        category="L2",
        required_params=["resource_id"],
    ),
    "flush_stuck_deploy": TaskDefinition(
        name="flush_stuck_deploy",
        description="Clear stuck deployment and trigger controlled retry/rollback",
        category="L2",
        required_params=[],
    ),
    "rotate_service_credentials": TaskDefinition(
        name="rotate_service_credentials",
        description="Rotate app/cloud credentials with controlled rollout",
        category="L2",
        required_params=[],
    ),
    # L3: advanced engineering and strategy tasks
    "root_cause_analysis": TaskDefinition(
        name="root_cause_analysis",
        description="Perform deep RCA using telemetry, deploy history, and infra changes",
        category="L3",
        required_params=[],
    ),
    "execute_failover_plan": TaskDefinition(
        name="execute_failover_plan",
        description="Execute regional failover strategy under incident command",
        category="L3",
        required_params=[],
    ),
    "disaster_recovery_drill": TaskDefinition(
        name="disaster_recovery_drill",
        description="Run planned DR drill and validate recovery objectives",
        category="L3",
        required_params=[],
    ),
    "security_forensics_workflow": TaskDefinition(
        name="security_forensics_workflow",
        description="Coordinate cloud security forensics and evidence capture",
        category="L3",
        required_params=[],
    ),
    "cost_optimization_review": TaskDefinition(
        name="cost_optimization_review",
        description="Analyze spend anomalies and optimization candidates",
        category="L3",
        required_params=[],
    ),
    "post_incident_review": TaskDefinition(
        name="post_incident_review",
        description="Create PIR timeline, causes, actions, and preventive controls",
        category="L3",
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
        "collect_ticket_context": lambda: {
            "resource_id": request.resource_id,
            "instance_status": provider.check_instance_status(request.resource_id)
            if request.resource_id
            else {"skipped": "resource_id not provided"},
            "network": provider.check_network_health(request.resource_id),
            "events": provider.list_recent_events(request.resource_id, int(request.params.get("limit", 20))),
        },
        "verify_backup_job_status": lambda: {
            "check": "backup_events_review",
            "events": provider.list_recent_events(request.resource_id, int(request.params.get("limit", 25))),
            "note": "Inspect event list for backup job success/failure markers.",
        },
        "check_service_error_budget": lambda: _manual_activity_result(
            request,
            [
                "Open observability dashboard and inspect 1h/6h/24h SLO burn rates.",
                "Compare against deployment windows and alert suppression windows.",
                "Create or update incident ticket if burn rate crosses threshold.",
            ],
        ),
        "validate_ssl_certificate_expiry": lambda: _manual_activity_result(
            request,
            [
                "List certs for ingress/load balancer and collect expiry dates.",
                "Flag any certificate expiring within 30 days.",
                "Trigger certificate renewal workflow and attach proof in ticket.",
            ],
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
        "scale_instance_group": lambda: _manual_activity_result(
            request,
            [
                "Validate autoscaler policy and current capacity headroom.",
                "Apply scale action using approved change window.",
                "Monitor saturation and rollback if error rate increases.",
            ],
        ),
        "isolate_unhealthy_node": lambda: _manual_activity_result(
            request,
            [
                "Drain node from load balancer/service mesh target group.",
                "Capture logs, metrics, and system events for node.",
                "Decide repair, replacement, or rollback path.",
            ],
        ),
        "flush_stuck_deploy": lambda: _manual_activity_result(
            request,
            [
                "Identify blocked pipeline stage and owning deployment lock.",
                "Cancel or rollback failed release using release policy.",
                "Re-run deployment with canary verification.",
            ],
        ),
        "rotate_service_credentials": lambda: _manual_activity_result(
            request,
            [
                "Create new credential version in secret manager.",
                "Roll out consumers in phased deployment.",
                "Disable old credentials after successful verification.",
            ],
        ),
        "root_cause_analysis": lambda: _manual_activity_result(
            request,
            [
                "Build a minute-by-minute timeline from alerts, deploys, and infra changes.",
                "Correlate causal signal using logs/metrics/traces and control-plane events.",
                "Document root cause, contributing factors, and validated remediation.",
            ],
        ),
        "execute_failover_plan": lambda: _manual_activity_result(
            request,
            [
                "Declare failover command and freeze non-essential changes.",
                "Switch traffic to standby region and verify data consistency checks.",
                "Track customer impact and publish restoration milestones.",
            ],
        ),
        "disaster_recovery_drill": lambda: _manual_activity_result(
            request,
            [
                "Run DR playbook in controlled window with stakeholders online.",
                "Measure RTO/RPO against policy targets.",
                "Record gaps and assign follow-up engineering actions.",
            ],
        ),
        "security_forensics_workflow": lambda: _manual_activity_result(
            request,
            [
                "Preserve evidence snapshots and establish chain-of-custody records.",
                "Analyze IAM activity, unusual network paths, and data exfiltration signals.",
                "Coordinate containment and legal/compliance reporting requirements.",
            ],
        ),
        "cost_optimization_review": lambda: _manual_activity_result(
            request,
            [
                "Analyze spend deltas by service, account/subscription/project, and environment.",
                "Identify idle resources and rightsizing opportunities.",
                "Publish optimization plan with projected monthly savings.",
            ],
        ),
        "post_incident_review": lambda: _manual_activity_result(
            request,
            [
                "Finalize incident timeline and customer-impact statement.",
                "Capture corrective and preventive actions with owners and due dates.",
                "Review runbook updates and training actions for next response cycle.",
            ],
        ),
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


def _manual_activity_result(request: TaskExecutionRequest, steps: list[str]) -> dict:
    return {
        "automation_mode": "human_in_the_loop",
        "task": request.task,
        "resource_id": request.resource_id,
        "params": request.params,
        "manual_steps": steps,
        "note": "This task requires engineer validation and controlled execution.",
    }


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
        "execute_failover_plan": ["Engage incident commander and business continuity leads immediately."],
        "security_forensics_workflow": ["Preserve volatile evidence before containment actions."],
    }
    return task_hints.get(task_name, []) + fallback
