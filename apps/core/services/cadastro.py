"""Helpers for base cadastro write/archive/delete with audit."""
from __future__ import annotations

from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.core.permissions import can_hard_delete
from apps.core.services.audit import log_action


def request_ip(request):
    return request.META.get("REMOTE_ADDR")


def audit(request, action: str, obj, message: str, payload: dict | None = None):
    log_action(
        actor=request.user,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=getattr(obj, "pk", ""),
        message=message,
        payload=payload or {},
        ip_address=request_ip(request),
    )


def archive_object(request, obj, *, redirect_to):
    if hasattr(obj, "archive"):
        obj.archive()
    else:
        obj.is_active = False
        if hasattr(obj, "archived_at"):
            obj.archived_at = timezone.now()
        obj.save()
    audit(request, "delete", obj, f"{obj.__class__.__name__} desativado: {obj}")
    messages.success(request, "Registro desativado.")
    return redirect(redirect_to)


def restore_object(request, obj, *, redirect_to):
    obj.is_active = True
    fields = ["is_active"]
    if hasattr(obj, "archived_at"):
        obj.archived_at = None
        fields.append("archived_at")
    if hasattr(obj, "updated_at"):
        fields.append("updated_at")
    obj.save(update_fields=fields)
    audit(request, "update", obj, f"{obj.__class__.__name__} reativado: {obj}")
    messages.success(request, "Registro reativado.")
    return redirect(redirect_to)


def hard_delete_object(request, obj, *, redirect_to, blocked: bool = False, block_message: str = ""):
    if not can_hard_delete(request.user):
        return render(request, "admin_panel/forbidden.html", status=403)
    if blocked:
        messages.error(request, block_message or "Não é possível excluir este registro.")
        return redirect(redirect_to)
    label = str(obj)
    model_name = obj.__class__.__name__
    pk = obj.pk
    try:
        obj.delete()
    except ProtectedError:
        messages.error(request, "Há registros vinculados. Desative em vez de excluir.")
        return redirect(redirect_to)
    log_action(
        actor=request.user,
        action="delete",
        object_type=model_name,
        object_id=pk,
        message=f"Exclusão definitiva: {label}",
        ip_address=request_ip(request),
    )
    messages.success(request, "Registro excluído.")
    return redirect(redirect_to)
