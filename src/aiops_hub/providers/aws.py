from typing import Any

from aiops_hub.providers.base import CloudProvider


class AWSProvider(CloudProvider):
    name = "aws"

    def check_instance_status(self, resource_id: str) -> dict[str, Any]:
        result = self.run_cli_json(
            [
                "aws",
                "ec2",
                "describe-instance-status",
                "--instance-ids",
                resource_id,
                "--include-all-instances",
                "--output",
                "json",
            ]
        )
        return result.model_dump()

    def restart_instance(self, resource_id: str) -> dict[str, Any]:
        result = self.run_cli_json(
            ["aws", "ec2", "reboot-instances", "--instance-ids", resource_id, "--output", "json"]
        )
        return result.model_dump()

    def check_storage_health(self, resource_id: str | None = None) -> dict[str, Any]:
        command = ["aws", "ec2", "describe-volume-status", "--output", "json"]
        if resource_id:
            command.extend(["--volume-ids", resource_id])
        return self.run_cli_json(command).model_dump()

    def check_network_health(self, resource_id: str | None = None) -> dict[str, Any]:
        command = ["aws", "ec2", "describe-network-interfaces", "--output", "json"]
        if resource_id:
            command.extend(["--network-interface-ids", resource_id])
        return self.run_cli_json(command).model_dump()

    def list_recent_events(self, resource_id: str | None = None, limit: int = 10) -> dict[str, Any]:
        command = [
            "aws",
            "cloudtrail",
            "lookup-events",
            "--max-results",
            str(limit),
            "--output",
            "json",
        ]
        if resource_id:
            command.extend(
                [
                    "--lookup-attributes",
                    f"AttributeKey=ResourceName,AttributeValue={resource_id}",
                ]
            )
        return self.run_cli_json(command).model_dump()
