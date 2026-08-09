"""Pedagogical labels for teacher-facing UI (no internal model names)."""
from __future__ import annotations

from apps.interventions.services.settings import SKILL_DISPLAY_OVERRIDES


def first_name(full_name: str) -> str:
    parts = (full_name or "").strip().split()
    return parts[0] if parts else full_name or ""


def skill_label(skill) -> str:
    dimension = getattr(skill, "dimension", None)
    code = getattr(dimension, "code", "") or ""
    if code in SKILL_DISPLAY_OVERRIDES:
        return SKILL_DISPLAY_OVERRIDES[code]
    if dimension and getattr(dimension, "name", ""):
        return dimension.name
    return getattr(skill, "name", "") or ""


def template_activity_title(template) -> str:
    if template is None:
        return "Atividade sugerida"
    lines = template.activities_list() if hasattr(template, "activities_list") else []
    if lines:
        return lines[0]
    return template.title


def day_greeting(*, hour: int | None = None) -> str:
    if hour is None:
        from django.utils import timezone

        hour = timezone.localtime().hour
    if hour < 12:
        return "Bom dia"
    if hour < 18:
        return "Boa tarde"
    return "Boa noite"
