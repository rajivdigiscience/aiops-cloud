import hashlib

from fastapi import Header, HTTPException

from aiops_hub.config import get_settings
from aiops_hub.models import AuthContext, RoleName


def _split_keys(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def _build_key_map() -> dict[str, RoleName]:
    settings = get_settings()
    key_map: dict[str, RoleName] = {}
    for key in _split_keys(settings.api_keys_viewer):
        key_map[key] = "viewer"
    for key in _split_keys(settings.api_keys_operator):
        key_map[key] = "operator"
    for key in _split_keys(settings.api_keys_admin):
        key_map[key] = "admin"
    return key_map


def fingerprint(api_key: str) -> str:
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return digest[:12]


def require_auth(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> AuthContext:
    settings = get_settings()

    if not settings.require_api_key:
        return AuthContext(role="admin", key_fingerprint="anonymous-admin")

    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is required")

    role = _build_key_map().get(x_api_key)
    if not role:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return AuthContext(role=role, key_fingerprint=fingerprint(x_api_key))


def require_min_role(auth: AuthContext, minimum: RoleName) -> None:
    weights: dict[RoleName, int] = {"viewer": 1, "operator": 2, "admin": 3}
    if weights[auth.role] < weights[minimum]:
        raise HTTPException(status_code=403, detail=f"{minimum} role required")
