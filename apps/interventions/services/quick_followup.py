"""Batch follow-up after an activity — evidence only, never formal scoring."""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.core.services.audit import log_action
from apps.evidences.models import Evidence
from apps.interventions.models import (
    ClassroomIntervention,
    FollowupResult,
    InterventionStatus,
    StudentIntervention,
)
from apps.interventions.services.settings import FOLLOWUP_EVIDENCE_TEXTS


VALID_RESULTS = set(FollowupResult.values)


@dataclass
class FollowupEntry:
    student_intervention: StudentIntervention
    result: str
    created: bool
    evidence: Evidence | None


@dataclass
class FollowupBatchResult:
    classroom_intervention: ClassroomIntervention | None
    entries: list[FollowupEntry]
    general_notes: str = ""


def evidence_text_for(*, result: str, activity: str) -> str:
    template = FOLLOWUP_EVIDENCE_TEXTS.get(result) or FOLLOWUP_EVIDENCE_TEXTS[FollowupResult.NOT_OBSERVED]
    return template.format(activity=activity)


@transaction.atomic
def record_batch_followup(
    *,
    user,
    interventions: list[StudentIntervention],
    results: dict[int, str],
    general_notes: str = "",
    classroom_intervention: ClassroomIntervention | None = None,
) -> FollowupBatchResult:
    now = timezone.now()
    activity = ""
    if classroom_intervention and classroom_intervention.template_id:
        activity = classroom_intervention.template.title
    elif interventions:
        first = interventions[0]
        activity = first.template.title if first.template_id else (first.activities.splitlines()[0] if first.activities else "atividade")
    activity = activity or "atividade"

    entries: list[FollowupEntry] = []
    for intervention in interventions:
        result = (results.get(intervention.pk) or results.get(intervention.student_id) or "").strip()
        if result not in VALID_RESULTS:
            continue
        already = intervention.has_followup and intervention.followup_result == result
        intervention.followup_result = result
        intervention.followup_recorded_at = now
        if result == FollowupResult.NOT_OBSERVED:
            intervention.status = InterventionStatus.IN_PROGRESS
        else:
            intervention.status = InterventionStatus.COMPLETED
        if general_notes and not intervention.observation:
            intervention.observation = general_notes
        elif general_notes and general_notes not in intervention.observation:
            intervention.observation = f"{intervention.observation}\n{general_notes}".strip()
        intervention.save(
            update_fields=["followup_result", "followup_recorded_at", "status", "observation", "updated_at"]
        )

        evidence = None
        description = evidence_text_for(result=result, activity=activity)
        if already:
            evidence = (
                Evidence.objects.filter(
                    student_id=intervention.student_id,
                    enrollment_id=intervention.enrollment_id,
                    skill_id=intervention.skill_id,
                    recorded_by=user,
                    file_type=Evidence.FileType.TEXT,
                    description=description,
                    is_active=True,
                )
                .order_by("-recorded_at")
                .first()
            )
        if evidence is None:
            # Idempotency: same day + same result + same skill + same actor
            evidence = (
                Evidence.objects.filter(
                    student_id=intervention.student_id,
                    enrollment_id=intervention.enrollment_id,
                    skill_id=intervention.skill_id,
                    recorded_by=user,
                    file_type=Evidence.FileType.TEXT,
                    description=description,
                    recorded_at__date=now.date(),
                    is_active=True,
                )
                .order_by("-recorded_at")
                .first()
            )
        created_evidence = False
        if evidence is None:
            evidence = Evidence.objects.create(
                enrollment=intervention.enrollment,
                student=intervention.student,
                skill=intervention.skill,
                recorded_by=user,
                description=description,
                file_type=Evidence.FileType.TEXT,
                visible_to_family=False,
            )
            created_evidence = True

        log_action(
            actor=user,
            action="update",
            object_type="StudentIntervention",
            object_id=intervention.pk,
            message="Acompanhamento rápido registrado",
            payload={
                "result": result,
                "student_id": intervention.student_id,
                "skill_id": intervention.skill_id,
                "evidence_id": evidence.pk,
                "created_evidence": created_evidence,
                "metric": "quick_followup",
                "not_formal_assessment": True,
            },
        )
        entries.append(
            FollowupEntry(
                student_intervention=intervention,
                result=result,
                created=not already,
                evidence=evidence,
            )
        )

    if classroom_intervention and entries:
        if all(e.student_intervention.has_followup for e in entries):
            if all(e.result == FollowupResult.NOT_OBSERVED for e in entries):
                classroom_intervention.status = InterventionStatus.IN_PROGRESS
            else:
                classroom_intervention.status = InterventionStatus.COMPLETED
        else:
            classroom_intervention.status = InterventionStatus.IN_PROGRESS
        if general_notes:
            classroom_intervention.observation = general_notes
        classroom_intervention.save(update_fields=["status", "observation", "updated_at"])
        log_action(
            actor=user,
            action="update",
            object_type="ClassroomIntervention",
            object_id=classroom_intervention.pk,
            message="Registro em lote da atividade",
            payload={
                "count": len(entries),
                "metric": "quick_followup_batch",
                "general_notes": bool(general_notes),
            },
        )

    return FollowupBatchResult(
        classroom_intervention=classroom_intervention,
        entries=entries,
        general_notes=general_notes,
    )


def followup_targets_for_classroom_intervention(classroom_intervention: ClassroomIntervention) -> list[StudentIntervention]:
    links = list(
        StudentIntervention.objects.filter(
            classroom_intervention=classroom_intervention,
            is_active=True,
        )
        .select_related("student", "enrollment", "skill", "template")
        .order_by("student__full_name")
    )
    if links:
        return links
    return []
