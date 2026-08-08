"""Rule-based intervention recommendations (no external AI)."""
from __future__ import annotations

from apps.interventions.models import InterventionTemplate


def recommend_template_for_result(*, skill, status_code: str):
    if status_code in {"demonstrated"}:
        return None
    return (
        InterventionTemplate.objects.filter(skill=skill, is_active=True)
        .order_by("id")
        .first()
    )
