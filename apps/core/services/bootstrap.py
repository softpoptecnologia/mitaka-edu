"""Platform catalog that must exist without seed_demo."""
from __future__ import annotations

from apps.accounts.models import Role
from apps.accessibility.services.catalog import ensure_default_features


def ensure_roles() -> dict[str, Role]:
    roles = {}
    for code, name in Role.Code.choices:
        role, _ = Role.objects.get_or_create(code=code, defaults={"name": name})
        if role.name != name:
            role.name = name
            role.save(update_fields=["name"])
        roles[code] = role
    return roles


def ensure_platform_catalog() -> None:
    ensure_roles()
    ensure_default_features()
