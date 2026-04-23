from typing import Any

from aiops_hub.providers.base import CloudProvider


class AzureProvider(CloudProvider):
    name = "azure"

    @staticmethod
    def _split_resource(resource_id: str) -> tuple[str, str]:
        if "/" in resource_id:
            rg, name = resource_id.split("/", 1)
            return rg, name
        return "", resource_id

    def check_instance_status(self, resource_id: str) -> dict[str, Any]:
        rg, name = self._split_resource(resource_id)
        command = ["az", "vm", "get-instance-view", "--name", name, "--output", "json"]
        if rg:
            command.extend(["--resource-group", rg])
        return self.run_cli_json(command).model_dump()

    def restart_instance(self, resource_id: str) -> dict[str, Any]:
        rg, name = self._split_resource(resource_id)
        command = ["az", "vm", "restart", "--name", name, "--output", "json"]
        if rg:
            command.extend(["--resource-group", rg])
        return self.run_cli_json(command).model_dump()

    def check_storage_health(self, resource_id: str | None = None) -> dict[str, Any]:
        if resource_id:
            rg, name = self._split_resource(resource_id)
            command = [
                "az",
                "storage",
                "account",
                "show",
                "--name",
                name,
                "--output",
                "json",
            ]
            if rg:
                command.extend(["--resource-group", rg])
            return self.run_cli_json(command).model_dump()
        return self.run_cli_json(["az", "storage", "account", "list", "--output", "json"]).model_dump()

    def check_network_health(self, resource_id: str | None = None) -> dict[str, Any]:
        if resource_id:
            rg, name = self._split_resource(resource_id)
            command = ["az", "network", "nic", "show", "--name", name, "--output", "json"]
            if rg:
                command.extend(["--resource-group", rg])
            return self.run_cli_json(command).model_dump()
        return self.run_cli_json(["az", "network", "nic", "list", "--output", "json"]).model_dump()

    def list_recent_events(self, resource_id: str | None = None, limit: int = 10) -> dict[str, Any]:
        command = ["az", "monitor", "activity-log", "list", "--max-events", str(limit), "--output", "json"]
        if resource_id:
            command.extend(["--resource-id", resource_id])
        return self.run_cli_json(command).model_dump()
