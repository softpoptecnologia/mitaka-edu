"""Apply a suggested pedagogical group using existing intervention/plan models."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.services.audit import log_action
from apps.interventions.models import (
    ClassroomIntervention,
    InterventionStatus,
    InterventionTemplate,
    StudentIntervention,
)
from apps.planning.models import PedagogicalPlan, PlanActivity
from apps.students.models import Enrollment


@dataclass
class AppliedGroupResult:
    classroom_intervention: ClassroomIntervention
    student_interventions: list[StudentIntervention]
    plan: PedagogicalPlan
    created: bool


@transaction.atomic
def apply_suggested_group(
    *,
    user,
    classroom,
    skill,
    student_ids: list[int],
    template: InterventionTemplate | None = None,
    starts_on=None,
) -> AppliedGroupResult:
    starts_on = starts_on or timezone.localdate()
    classroom_student_ids = set(
        Enrollment.objects.filter(
            classroom=classroom,
            is_active=True,
            status=Enrollment.Status.ACTIVE,
            student_id__in=student_ids,
        ).values_list("student_id", flat=True)
    )
    ordered_ids = [sid for sid in student_ids if sid in classroom_student_ids]
    if not ordered_ids:
        raise ValueError("Nenhum estudante desta turma foi informado.")

    if template is None:
        template = (
            InterventionTemplate.objects.filter(skill=skill, is_active=True).order_by("id").first()
        )

    existing = (
        ClassroomIntervention.objects.filter(
            classroom=classroom,
            skill=skill,
            template=template,
            starts_on=starts_on,
            is_active=True,
            status__in=[InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS],
        )
        .order_by("-id")
        .first()
    )
    created = existing is None
    if existing:
        intervention = existing
        intervention.status = InterventionStatus.IN_PROGRESS
        intervention.responsible = user
        intervention.save(update_fields=["status", "responsible", "updated_at"])
    else:
        intervention = ClassroomIntervention.objects.create(
            classroom=classroom,
            skill=skill,
            template=template,
            responsible=user,
            objective=template.objective if template else f"Fortalecer {skill.name}",
            activities=template.suggested_activities if template else "",
            starts_on=starts_on,
            ends_on=starts_on + timedelta(days=template.suggested_duration_days) if template else None,
            status=InterventionStatus.IN_PROGRESS,
        )

    enrollments = {
        e.student_id: e
        for e in Enrollment.objects.filter(
            classroom=classroom,
            is_active=True,
            status=Enrollment.Status.ACTIVE,
            student_id__in=ordered_ids,
        ).select_related("student")
    }
    student_interventions = []
    for student_id in ordered_ids:
        enrollment = enrollments[student_id]
        student_iv, _ = StudentIntervention.objects.get_or_create(
            enrollment=enrollment,
            student_id=student_id,
            skill=skill,
            classroom_intervention=intervention,
            defaults={
                "template": template,
                "responsible": user,
                "objective": intervention.objective,
                "activities": intervention.activities,
                "starts_on": starts_on,
                "ends_on": intervention.ends_on,
                "status": InterventionStatus.IN_PROGRESS,
            },
        )
        if student_iv.status == InterventionStatus.PLANNED:
            student_iv.status = InterventionStatus.IN_PROGRESS
            student_iv.responsible = user
            student_iv.save(update_fields=["status", "responsible", "updated_at"])
        student_interventions.append(student_iv)

    plan = PedagogicalPlan.objects.filter(classroom_intervention=intervention, is_active=True).first()
    if plan is None:
        plan = PedagogicalPlan.objects.create(
            classroom=classroom,
            title=f"Atividade — {template.title if template else skill.name}",
            skill=skill,
            created_by=user,
            classroom_intervention=intervention,
            duration_minutes=getattr(template, "suggested_activity_minutes", None),
            source=PedagogicalPlan.Source.SUGGESTED,
            notes="Sugestão aceita pelo professor a partir do agrupamento da turma.",
        )
        if template:
            for i, line in enumerate(template.activities_list()):
                PlanActivity.objects.create(
                    plan=plan,
                    title=line,
                    order=i,
                    duration_minutes=template.suggested_activity_minutes if i == 0 else None,
                )
        else:
            PlanActivity.objects.create(plan=plan, title=f"Trabalhar {skill.name}", order=0)

    log_action(
        actor=user,
        action="create" if created else "update",
        object_type="ClassroomIntervention",
        object_id=intervention.pk,
        message="Atividade aplicada com o grupo sugerido",
        payload={
            "classroom_id": classroom.pk,
            "skill_id": skill.pk,
            "template_id": getattr(template, "pk", None),
            "student_ids": ordered_ids,
            "created": created,
            "metric": "group_applied",
        },
    )
    return AppliedGroupResult(
        classroom_intervention=intervention,
        student_interventions=student_interventions,
        plan=plan,
        created=created,
    )
