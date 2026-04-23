from typing import Any

from aiops_hub.providers.base import CloudProvider


class GCPProvider(CloudProvider):
    name = "gcp"

    @staticmethod
    def _split_instance(resource_id: str) -> tuple[str | None, str]:
        if "/" in resource_id:
            zone, name = resource_id.split("/", 1)
            return zone, name
        return None, resource_id

    def check_instance_status(self, resource_id: str) -> dict[str, Any]:
        zone, name = self._split_instance(resource_id)
        command = ["gcloud", "compute", "instances", "describe", name, "--format=json"]
        if zone:
            command.extend(["--zone", zone])
        return self.run_cli_json(command).model_dump()

    def restart_instance(self, resource_id: str) -> dict[str, Any]:
        zone, name = self._split_instance(resource_id)
        command = ["gcloud", "compute", "instances", "reset", name, "--format=json"]
        if zone:
            command.extend(["--zone", zone])
        return self.run_cli_json(command).model_dump()

    def check_storage_health(self, resource_id: str | None = None) -> dict[str, Any]:
        if resource_id:
            bucket = resource_id if resource_id.startswith("gs://") else f"gs://{resource_id}"
            return self.run_cli_json(["gcloud", "storage", "buckets", "describe", bucket, "--format=json"]).model_dump()
        return self.run_cli_json(["gcloud", "storage", "buckets", "list", "--format=json"]).model_dump()

    def check_network_health(self, resource_id: str | None = None) -> dict[str, Any]:
        if resource_id:
            return self.run_cli_json(
                ["gcloud", "compute", "networks", "describe", resource_id, "--format=json"]
            ).model_dump()
        return self.run_cli_json(["gcloud", "compute", "networks", "list", "--format=json"]).model_dump()

    def list_recent_events(self, resource_id: str | None = None, limit: int = 10) -> dict[str, Any]:
        query = "severity>=WARNING"
        if resource_id:
            query += f' AND resource.labels.instance_id="{resource_id}"'
        return self.run_cli_json(
            [
                "gcloud",
                "logging",
                "read",
                query,
                "--limit",
                str(limit),
                "--format=json",
            ]
        ).model_dump()
