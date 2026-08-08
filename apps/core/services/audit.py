"""Audit logging service."""
from __future__ import annotations

from typing import Any

from apps.core.models import AuditLog


def log_action(
    *,
    actor=None,
    action: str,
    object_type: str = "",
    object_id: str | int = "",
    message: str = "",
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id != "" else "",
        message=message,
        payload=payload or {},
        ip_address=ip_address,
    )
