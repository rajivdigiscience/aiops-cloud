class ProviderError(RuntimeError):
    """Raised for provider-level operational errors."""


class TaskNotFoundError(ValueError):
    """Raised when a runbook task does not exist."""
