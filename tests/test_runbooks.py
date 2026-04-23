from aiops_hub.models import TaskExecutionRequest
from aiops_hub.providers.base import CloudProvider
from aiops_hub.runbooks import execute_task


class DummyProvider(CloudProvider):
    name = "aws"

    def check_instance_status(self, resource_id: str):
        return {"ok": True, "instance": resource_id}

    def restart_instance(self, resource_id: str):
        return {"ok": True, "restarted": resource_id}

    def check_storage_health(self, resource_id: str | None = None):
        return {"ok": True, "storage": resource_id or "all"}

    def check_network_health(self, resource_id: str | None = None):
        return {"ok": True, "network": resource_id or "all"}

    def list_recent_events(self, resource_id: str | None = None, limit: int = 10):
        return {"ok": True, "events": [], "limit": limit}


def test_execute_check_instance_status_success():
    provider = DummyProvider()
    req = TaskExecutionRequest(provider="aws", task="check_instance_status", resource_id="i-123")

    result = execute_task(provider, req)

    assert result.status == "success"
    assert result.output["instance"] == "i-123"


def test_execute_diagnostic_bundle_success():
    provider = DummyProvider()
    req = TaskExecutionRequest(provider="aws", task="diagnostic_bundle", resource_id="i-123", params={"limit": 3})

    result = execute_task(provider, req)

    assert result.status == "success"
    assert result.output["events"]["limit"] == 3
