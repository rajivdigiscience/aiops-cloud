import json
import subprocess
from abc import ABC, abstractmethod
from typing import Any

from aiops_hub.config import get_settings
from aiops_hub.models import ProviderCommandResult


class CloudProvider(ABC):
    name: str

    @abstractmethod
    def check_instance_status(self, resource_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def restart_instance(self, resource_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def check_storage_health(self, resource_id: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def check_network_health(self, resource_id: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_recent_events(self, resource_id: str | None = None, limit: int = 10) -> dict[str, Any]:
        raise NotImplementedError

    def run_cli_json(self, command: list[str]) -> ProviderCommandResult:
        settings = get_settings()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=settings.command_timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return ProviderCommandResult(
                ok=False,
                command=command,
                error=f"CLI not installed or not in PATH: {command[0]}",
            )
        except subprocess.TimeoutExpired:
            return ProviderCommandResult(
                ok=False,
                command=command,
                error=f"Command timed out after {settings.command_timeout_seconds}s",
            )

        output = completed.stdout.strip()
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            return ProviderCommandResult(
                ok=False,
                command=command,
                raw_output=output,
                error=stderr or f"Command failed with code {completed.returncode}",
            )

        if not output:
            return ProviderCommandResult(ok=True, command=command, raw_output="", parsed={})

        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = {"text": output}

        return ProviderCommandResult(ok=True, command=command, raw_output=output, parsed=parsed)
