"""Recommend when a skill may be observed again — never auto-starts sessions."""
from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.interventions.models import FollowupResult, InterventionStatus
from apps.interventions.services.labels import first_name, skill_label
from apps.interventions.services.settings import (
    DEFAULT_REASSESSMENT_DAYS,
    REASSESSMENT_DAYS_NEEDS_SUPPORT,
)


@dataclass
class ReassessmentSuggestion:
    classroom_id: int
    student_id: int
    student_name: str
    enrollment_id: int
    skill_id: int
    skill_name: str
    intervention_id: int | None
    reason: str
    days_since: int
    instrument_id: int | None = None


def reassessment_days_for(followup_result: str | None) -> int | None:
    if followup_result == FollowupResult.NOT_OBSERVED:
        return None
    if followup_result == FollowupResult.NEEDS_MORE_SUPPORT:
        return REASSESSMENT_DAYS_NEEDS_SUPPORT
    return DEFAULT_REASSESSMENT_DAYS


def suggestions_for_snapshot(snapshot) -> list[ReassessmentSuggestion]:
    today = timezone.localdate()
    now = timezone.now()
    items: list[ReassessmentSuggestion] = []
    seen: set[tuple[int, int]] = set()

    for record in snapshot.records:
        for intervention in record.interventions:
            if intervention.status == InterventionStatus.CANCELLED:
                continue
            if not intervention.has_followup and intervention.status != InterventionStatus.COMPLETED:
                continue
            wait_days = reassessment_days_for(intervention.followup_result or None)
            if wait_days is None:
                continue
            reference = intervention.followup_recorded_at or intervention.updated_at or intervention.created_at
            if reference is None:
                continue
            elapsed = (now - reference).days if hasattr(reference, "date") else (today - reference).days
            if elapsed < wait_days:
                continue
            last_session = record.last_session_by_skill_id.get(intervention.skill_id)
            if last_session and last_session.started_at and last_session.started_at >= reference:
                continue
            key = (record.student_id, intervention.skill_id)
            if key in seen:
                continue
            seen.add(key)
            instruments = snapshot.instruments_by_skill_id.get(intervention.skill_id) or []
            skill = intervention.skill
            items.append(
                ReassessmentSuggestion(
                    classroom_id=snapshot.classroom.pk,
                    student_id=record.student_id,
                    student_name=record.student.full_name,
                    enrollment_id=record.enrollment.pk,
                    skill_id=intervention.skill_id,
                    skill_name=skill_label(skill),
                    intervention_id=intervention.pk,
                    reason=(
                        f"Com base nos registros recentes, pode ser um bom momento para observar "
                        f"novamente {skill_label(skill)} com {first_name(record.student.full_name)}."
                    ),
                    days_since=elapsed,
                    instrument_id=instruments[0].pk if instruments else None,
                )
            )
    return items
