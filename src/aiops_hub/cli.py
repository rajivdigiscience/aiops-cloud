import json

import typer
import uvicorn

from aiops_hub.models import AuthContext, IncidentTriageRequest, TaskExecutionRequest
from aiops_hub.service import AIOpsService

app = typer.Typer(help="AI Ops Hub CLI")
service = AIOpsService()


def _auth(role: str) -> AuthContext:
    return AuthContext(role=role, key_fingerprint="cli-local")  # type: ignore[arg-type]


@app.command()
def api(host: str = "0.0.0.0", port: int = 8080):
    """Run FastAPI server."""
    uvicorn.run("aiops_hub.api:app", host=host, port=port, reload=False)


@app.command("providers")
def list_providers():
    """List supported cloud providers."""
    typer.echo(json.dumps(service.list_providers(), indent=2))


@app.command("tasks")
def list_tasks():
    """List supported L1/L2 tasks."""
    data = [t.model_dump() for t in service.list_tasks()]
    typer.echo(json.dumps(data, indent=2))


@app.command("run")
def run_task(
    provider: str = typer.Option(..., help="aws|azure|gcp"),
    task: str = typer.Option(..., help="Runbook task name"),
    resource_id: str = typer.Option("", help="Resource id, provider-specific"),
    limit: int = typer.Option(10, help="Event limit for event tasks"),
    role: str = typer.Option("admin", help="viewer|operator|admin"),
):
    """Run L1/L2 task against provider."""
    payload = TaskExecutionRequest(
        provider=provider,  # type: ignore[arg-type]
        task=task,
        resource_id=resource_id or None,
        params={"limit": limit},
    )
    response = service.execute_task_with_controls(payload, _auth(role))
    typer.echo(json.dumps(response.model_dump(), indent=2))


@app.command("triage")
def triage(
    provider: str = typer.Option(..., help="aws|azure|gcp"),
    title: str = typer.Option(...),
    description: str = typer.Option(...),
    logs: str = typer.Option(""),
    role: str = typer.Option("operator", help="viewer|operator|admin"),
):
    """Run AI-based incident triage."""
    payload = IncidentTriageRequest(
        provider=provider,  # type: ignore[arg-type]
        title=title,
        description=description,
        logs=logs or None,
    )
    response = service.triage_incident(payload, _auth(role))
    typer.echo(json.dumps(response.model_dump(), indent=2))


@app.command("approvals")
def approvals(status: str = typer.Option("", help="pending|approved|rejected"), limit: int = 100):
    data = [item.model_dump() for item in service.list_approvals(status=status or None, limit=limit)]
    typer.echo(json.dumps(data, indent=2))


@app.command("review")
def review(approval_id: str, approve: bool = True, note: str = "", execute_on_approve: bool = True):
    response = service.review_approval(
        approval_id,
        approve=approve,
        note=note,
        execute_on_approve=execute_on_approve,
        reviewer=_auth("admin"),
    )
    typer.echo(json.dumps(response.model_dump(), indent=2))


@app.command("audit")
def audit(limit: int = 100, action: str = "", status: str = ""):
    data = [
        item.model_dump()
        for item in service.list_audit(limit=limit, action=action or None, status=status or None)
    ]
    typer.echo(json.dumps(data, indent=2))


if __name__ == "__main__":
    app()
