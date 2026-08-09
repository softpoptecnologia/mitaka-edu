"""Deterministic lesson proposal from classroom needs, groups and templates."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.services.audit import log_action
from apps.interventions.services.apply_group import apply_suggested_group
from apps.interventions.services.grouping import suggest_groups
from apps.interventions.services.labels import first_name
from apps.interventions.services.settings import (
    CLOSING_MINUTES,
    DEFAULT_ACTIVITY_MINUTES,
    LESSON_DURATIONS,
    MAX_PRIORITY_SKILLS_PER_LESSON,
    MIN_ACTIVITY_MINUTES,
    TEMPLATE_REPEAT_AVOID_DAYS,
    WELCOME_MINUTES,
)
from apps.interventions.services.snapshot import ClassroomSnapshot
from apps.planning.models import PedagogicalPlan, PlanActivity


@dataclass
class LessonBlock:
    kind: str  # welcome | group | closing | observation
    title: str
    minutes: int
    description: str = ""
    skill_id: int | None = None
    skill_name: str = ""
    student_ids: list[int] = field(default_factory=list)
    student_names: list[str] = field(default_factory=list)
    template_id: int | None = None
    activity_title: str = ""
    accessibility_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "minutes": self.minutes,
            "description": self.description,
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "student_ids": self.student_ids,
            "student_names": self.student_names,
            "template_id": self.template_id,
            "activity_title": self.activity_title,
            "accessibility_notes": self.accessibility_notes,
        }


@dataclass
class LessonProposal:
    classroom_id: int
    classroom_name: str
    duration_minutes: int
    blocks: list[LessonBlock] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    why: str = ""

    @property
    def used_minutes(self) -> int:
        return sum(b.minutes for b in self.blocks)

    def to_dict(self) -> dict:
        return {
            "classroom_id": self.classroom_id,
            "classroom_name": self.classroom_name,
            "duration_minutes": self.duration_minutes,
            "used_minutes": self.used_minutes,
            "blocks": [b.to_dict() for b in self.blocks],
            "observations": self.observations,
            "why": self.why,
        }


def normalize_duration(value) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        minutes = 45
    if minutes in LESSON_DURATIONS:
        return minutes
    return max(20, min(minutes, 120))


def build_lesson_proposal(snapshot: ClassroomSnapshot, *, duration_minutes: int = 45) -> LessonProposal:
    duration = normalize_duration(duration_minutes)
    groups = [g for g in suggest_groups(snapshot) if g.kind != "consolidation"][:MAX_PRIORITY_SKILLS_PER_LESSON]
    blocks: list[LessonBlock] = [
        LessonBlock(
            kind="welcome",
            title="Acolhida e atividade coletiva",
            minutes=min(WELCOME_MINUTES, duration),
            description="Roda inicial com a turma toda.",
        )
    ]
    remaining = duration - blocks[0].minutes - min(CLOSING_MINUTES, duration // 4)
    observations = [
        "Observar participação.",
        "Registrar necessidade de apoio após a atividade.",
    ]
    recent_cutoff = timezone.now() - timedelta(days=TEMPLATE_REPEAT_AVOID_DAYS)
    used_template_ids = set()

    for group in groups:
        if remaining < MIN_ACTIVITY_MINUTES:
            break
        template = group.template
        if template and template.pk in used_template_ids:
            continue
        if template:
            recent_use = any(
                iv.template_id == template.pk
                and iv.created_at
                and iv.created_at >= recent_cutoff
                and iv.has_followup
                for rec in snapshot.records
                for iv in rec.interventions
            )
            if recent_use:
                continue
        minutes = getattr(template, "suggested_activity_minutes", None) or DEFAULT_ACTIVITY_MINUTES
        minutes = max(MIN_ACTIVITY_MINUTES, min(minutes, remaining))
        names = [first_name(s.full_name) for s in group.students]
        activity = group.activity_title
        blocks.append(
            LessonBlock(
                kind="group",
                title=f"Grupo {group.skill_name}",
                minutes=minutes,
                description=", ".join(names),
                skill_id=group.skill_id,
                skill_name=group.skill_name,
                student_ids=group.student_ids,
                student_names=[s.full_name for s in group.students],
                template_id=getattr(template, "pk", None),
                activity_title=activity,
                accessibility_notes=group.accessibility_notes,
            )
        )
        remaining -= minutes
        if template:
            used_template_ids.add(template.pk)
        if group.alternative_needed:
            observations.append(
                "Preparar alternativa de acesso para " + ", ".join(group.alternative_needed) + "."
            )

    pending = [r for r in snapshot.records if not r.has_completed_session]
    if pending and remaining >= MIN_ACTIVITY_MINUTES and len(blocks) < MAX_PRIORITY_SKILLS_PER_LESSON + 2:
        names = [first_name(r.student.full_name) for r in pending[:4]]
        minutes = min(DEFAULT_ACTIVITY_MINUTES, remaining)
        blocks.append(
            LessonBlock(
                kind="observation",
                title="Observação breve",
                minutes=minutes,
                description="Sondagem pendente: " + ", ".join(names),
                student_ids=[r.student_id for r in pending],
                student_names=[r.student.full_name for r in pending],
            )
        )
        remaining -= minutes
        observations.append(f"Preparar reavaliação/observação de {names[0]}.")

    closing = max(min(CLOSING_MINUTES, duration - sum(b.minutes for b in blocks)), 5) if duration >= 30 else max(
        duration - sum(b.minutes for b in blocks), 0
    )
    if closing:
        blocks.append(
            LessonBlock(
                kind="closing",
                title="Fechamento coletivo",
                minutes=closing,
                description="Retomar o que foi vivido e registrar impressões rápidas.",
            )
        )

    why_parts = []
    if groups:
        why_parts.append(
            "O plano parte das necessidades atuais da turma: "
            + ", ".join(f"{g.skill_name} ({g.size})" for g in groups)
            + "."
        )
    else:
        why_parts.append("Não há necessidades prioritárias no momento. O plano sugere consolidação coletiva.")
        if len(blocks) == 2:  # welcome + closing only
            blocks.insert(
                1,
                LessonBlock(
                    kind="group",
                    title="Atividade de consolidação",
                    minutes=max(duration - WELCOME_MINUTES - CLOSING_MINUTES, MIN_ACTIVITY_MINUTES),
                    description="Proposta coletiva para fortalecer o que a turma já acompanha bem.",
                ),
            )
            # recalc closing
            used = sum(b.minutes for b in blocks if b.kind != "closing")
            for block in blocks:
                if block.kind == "closing":
                    block.minutes = max(duration - used, 5)

    return LessonProposal(
        classroom_id=snapshot.classroom.pk,
        classroom_name=snapshot.classroom.name,
        duration_minutes=duration,
        blocks=blocks,
        observations=list(dict.fromkeys(observations)),
        why=" ".join(why_parts),
    )


@transaction.atomic
def accept_lesson_proposal(
    *,
    user,
    snapshot: ClassroomSnapshot,
    proposal: LessonProposal,
    adjusted: bool = False,
    apply_groups: bool = True,
) -> PedagogicalPlan:
    classroom = snapshot.classroom
    plan = PedagogicalPlan.objects.create(
        classroom=classroom,
        title=f"Plano da aula — {proposal.duration_minutes} min",
        created_by=user,
        duration_minutes=proposal.duration_minutes,
        source=PedagogicalPlan.Source.ADJUSTED if adjusted else PedagogicalPlan.Source.SUGGESTED,
        notes="\n".join(proposal.observations + ([proposal.why] if proposal.why else [])),
    )
    for index, block in enumerate(proposal.blocks):
        description_parts = [block.description]
        if block.student_names:
            description_parts.append("Estudantes: " + ", ".join(block.student_names))
        if block.activity_title:
            description_parts.append("Atividade: " + block.activity_title)
        if block.accessibility_notes:
            description_parts.extend(block.accessibility_notes)
        PlanActivity.objects.create(
            plan=plan,
            title=f"{block.minutes} min — {block.title}",
            description="\n".join(p for p in description_parts if p),
            order=index,
            duration_minutes=block.minutes,
        )
        if apply_groups and block.kind == "group" and block.skill_id and block.student_ids:
            skill = None
            template = snapshot.templates_by_skill_id.get(block.skill_id)
            for record in snapshot.records:
                status = record.status_for(block.skill_id)
                if status:
                    skill = status.skill
                    break
            if skill is None and template:
                skill = template.skill
            if skill is not None:
                applied = apply_suggested_group(
                    user=user,
                    classroom=classroom,
                    skill=skill,
                    student_ids=block.student_ids,
                    template=template,
                )
                if plan.classroom_intervention_id is None:
                    plan.classroom_intervention = applied.classroom_intervention
                    plan.skill = skill
                    plan.save(update_fields=["classroom_intervention", "skill", "updated_at"])

    log_action(
        actor=user,
        action="create",
        object_type="PedagogicalPlan",
        object_id=plan.pk,
        message="Plano de aula sugerido aceito" if not adjusted else "Plano de aula ajustado e aceito",
        payload={
            "classroom_id": classroom.pk,
            "duration_minutes": proposal.duration_minutes,
            "adjusted": adjusted,
            "metric": "lesson_accepted" if not adjusted else "lesson_adjusted",
        },
    )
    return plan
