from aiops_hub.providers.aws import AWSProvider
from aiops_hub.providers.azure import AzureProvider
from aiops_hub.providers.base import CloudProvider
from aiops_hub.providers.gcp import GCPProvider


def get_provider_registry() -> dict[str, CloudProvider]:
    return {
        "aws": AWSProvider(),
        "azure": AzureProvider(),
        "gcp": GCPProvider(),
    }
