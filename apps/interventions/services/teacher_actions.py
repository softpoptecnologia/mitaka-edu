"""Teacher action queue — actionable items only, scoped to the teacher."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.interventions.models import InterventionStatus
from apps.interventions.services.grouping import suggest_groups
from apps.interventions.services.labels import first_name, skill_label
from apps.interventions.services.reassessment import suggestions_for_snapshot
from apps.interventions.services.settings import (
    ACTION_ACCESSIBILITY_NOTICE,
    ACTION_ASSESSMENT_PENDING,
    ACTION_DISMISS_HOURS,
    ACTION_EVIDENCE_PENDING,
    ACTION_INDIVIDUAL_INTERVENTION,
    ACTION_INTERVENTION_FOLLOWUP,
    ACTION_REASSESSMENT_DUE,
    ACTION_SKILL_GROUP_INTERVENTION,
    FOLLOWUP_DUE_DAYS,
    MIN_GROUP_SIZE,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_ORDER,
)
from apps.interventions.services.snapshot import ClassroomSnapshot, load_snapshots_for_user


@dataclass
class TeacherAction:
    type: str
    priority: str
    classroom_id: int
    classroom_name: str
    title: str
    description: str
    action_url: str
    skill_id: int | None = None
    skill_name: str = ""
    student_ids: list[int] = field(default_factory=list)
    student_names: list[str] = field(default_factory=list)
    count: int = 0
    reason: str = ""
    why: str = ""
    recommended_action: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return (
            f"{self.type}:{self.classroom_id}:{self.skill_id or 0}:"
            f"{self.extra.get('intervention_id', 0)}"
        )

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "priority": self.priority,
            "classroom_id": self.classroom_id,
            "classroom_name": self.classroom_name,
            "title": self.title,
            "description": self.description,
            "action_url": self.action_url,
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "student_ids": self.student_ids,
            "student_names": self.student_names,
            "count": self.count or len(self.student_ids),
            "reason": self.reason,
            "why": self.why,
            "recommended_action": self.recommended_action,
            "key": self.key,
            "extra": self.extra,
        }


@dataclass
class TeacherActionQueue:
    actions: list[TeacherAction] = field(default_factory=list)
    snapshots: list[ClassroomSnapshot] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.actions)

    def for_classroom(self, classroom_id: int) -> list[TeacherAction]:
        return [a for a in self.actions if a.classroom_id == classroom_id]

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "actions": [a.to_dict() for a in self.actions],
        }


def build_teacher_action_queue(user) -> TeacherActionQueue:
    snapshots = load_snapshots_for_user(user)
    dismissed = dismissed_keys_for(user)
    actions: list[TeacherAction] = []
    for snapshot in snapshots:
        actions.extend(build_classroom_actions(snapshot))
    actions = [a for a in actions if a.key not in dismissed]
    actions.sort(key=lambda a: (PRIORITY_ORDER.get(a.priority, 9), -a.count, a.classroom_name, a.title))
    return TeacherActionQueue(actions=actions, snapshots=snapshots)


def build_classroom_actions(snapshot: ClassroomSnapshot) -> list[TeacherAction]:
    classroom = snapshot.classroom
    actions: list[TeacherAction] = []
    actions.extend(_assessment_actions(snapshot))
    actions.extend(_group_and_individual_actions(snapshot))
    actions.extend(_followup_actions(snapshot))
    actions.extend(_reassessment_actions(snapshot))
    actions.extend(_accessibility_notices(snapshot, actions))
    for action in actions:
        action.classroom_id = classroom.pk
        action.classroom_name = classroom.name
    return actions


def dismiss_action(*, user, action_key: str, classroom_id: int | None = None) -> None:
    from apps.core.services.audit import log_action

    log_action(
        actor=user,
        action="update",
        object_type="TeacherActionDismiss",
        object_id=action_key,
        message="Recomendação ignorada pelo professor",
        payload={"classroom_id": classroom_id, "key": action_key},
    )


def dismissed_keys_for(user) -> set[str]:
    since = timezone.now() - timedelta(hours=ACTION_DISMISS_HOURS)
    return set(
        AuditLog.objects.filter(
            actor=user,
            object_type="TeacherActionDismiss",
            created_at__gte=since,
        ).values_list("object_id", flat=True)
    )


def _assessment_actions(snapshot: ClassroomSnapshot) -> list[TeacherAction]:
    pending_records = []
    details = []
    for record in snapshot.records:
        missing = []
        for skill_id, instruments in snapshot.instruments_by_skill_id.items():
            if not instruments:
                continue
            if skill_id not in record.completed_skill_ids:
                missing.append(instruments[0])
        if missing and not record.has_completed_session:
            pending_records.append(record)
            details.append((record, missing))
        elif missing and len(missing) == len(snapshot.instruments_by_skill_id):
            pending_records.append(record)
            details.append((record, missing))
        elif missing and not record.needs_attention:
            # already observed in some skills; only surface if they have zero sessions
            continue
        elif missing and not record.has_completed_session:
            pending_records.append(record)
            details.append((record, missing))

    # Students with no completed session at all
    none_completed = [r for r in snapshot.records if not r.has_completed_session]
    if not none_completed:
        return []

    students = none_completed
    names = [r.student.full_name for r in students]
    first = first_name(students[0].student.full_name)
    missing_label = ""
    if details:
        first_missing = details[0][1][0] if details[0][1] else None
        if first_missing:
            missing_label = skill_label(first_missing.skill)
    title = f"{len(students)} sondagens pendentes" if len(students) > 1 else f"{first} ainda precisa realizar sondagem"
    description = (
        f"{first} ainda precisa realizar a sondagem de {missing_label}."
        if missing_label and len(students) == 1
        else "Há estudantes aguardando observação nesta turma."
    )
    return [
        TeacherAction(
            type=ACTION_ASSESSMENT_PENDING,
            priority=PRIORITY_MEDIUM,
            classroom_id=snapshot.classroom.pk,
            classroom_name=snapshot.classroom.name,
            title=title,
            description=description,
            action_url=reverse("teacher:classroom", args=[snapshot.classroom.pk]) + "?filtro=pendentes",
            student_ids=[r.student_id for r in students],
            student_names=names,
            count=len(students),
            reason=description,
            why="Ainda não há observação registrada para estes estudantes no ano letivo ativo.",
            recommended_action="Iniciar observação",
        )
    ]


def _group_and_individual_actions(snapshot: ClassroomSnapshot) -> list[TeacherAction]:
    actions = []
    for group in suggest_groups(snapshot):
        if group.kind == "consolidation":
            continue
        is_group = group.size >= MIN_GROUP_SIZE
        action_type = ACTION_SKILL_GROUP_INTERVENTION if is_group else ACTION_INDIVIDUAL_INTERVENTION
        url = reverse("teacher:suggested_group", args=[snapshot.classroom.pk, group.skill_id])
        needs_support = 0
        for sid in group.student_ids:
            record = snapshot.records_by_student_id.get(sid)
            status = record.status_for(group.skill_id) if record else None
            if status and status.status_code in {"needs_support", "not_observed"}:
                needs_support += 1
        priority = PRIORITY_HIGH if needs_support >= 4 else PRIORITY_MEDIUM
        title = (
            f"{group.size} crianças precisam trabalhar {group.skill_name}"
            if is_group
            else f"{first_name(group.students[0].full_name)} precisa trabalhar {group.skill_name}"
        )
        actions.append(
            TeacherAction(
                type=action_type,
                priority=priority,
                classroom_id=snapshot.classroom.pk,
                classroom_name=snapshot.classroom.name,
                title=title,
                description=group.reason,
                action_url=url,
                skill_id=group.skill_id,
                skill_name=group.skill_name,
                student_ids=group.student_ids,
                student_names=[s.full_name for s in group.students],
                count=group.size,
                reason=group.reason,
                why=group.why,
                recommended_action="Trabalhar agora" if is_group else "Ver sugestão",
                extra={"template_id": getattr(group.template, "pk", None), "accessibility_notes": group.accessibility_notes},
            )
        )
    return actions


def _followup_actions(snapshot: ClassroomSnapshot) -> list[TeacherAction]:
    actions = []
    today = timezone.localdate()
    seen_ci = set()
    for ci in snapshot.classroom_interventions:
        if ci.status not in {InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS}:
            continue
        links = [r for rec in snapshot.records for r in rec.interventions if r.classroom_intervention_id == ci.pk]
        if links and all(link.has_followup for link in links):
            continue
        if not links:
            # classroom intervention without student links still needs follow-up after start date
            if ci.starts_on and ci.starts_on > today:
                continue
        due = True
        if ci.starts_on and (today - ci.starts_on).days < FOLLOWUP_DUE_DAYS and ci.status == InterventionStatus.PLANNED:
            due = (today - ci.starts_on).days >= 0
        if not due:
            continue
        seen_ci.add(ci.pk)
        activity = ci.template.title if ci.template_id else skill_label(ci.skill)
        count = len(links) or 1
        actions.append(
            TeacherAction(
                type=ACTION_INTERVENTION_FOLLOWUP,
                priority=PRIORITY_HIGH,
                classroom_id=snapshot.classroom.pk,
                classroom_name=snapshot.classroom.name,
                title="Atividade realizada aguardando registro" if count == 1 else f"{count} acompanhamentos aguardando registro",
                description=f"Como foi a atividade {activity}?",
                action_url=reverse("teacher:quick_followup", args=[ci.pk]),
                skill_id=ci.skill_id,
                skill_name=skill_label(ci.skill),
                student_ids=[link.student_id for link in links],
                student_names=[link.student.full_name for link in links] if links else [],
                count=count,
                reason="A atividade já pode ser registrada em lote.",
                why="Há intervenção em andamento sem registro mínimo de acompanhamento.",
                recommended_action="Registrar agora",
                extra={"intervention_id": ci.pk},
            )
        )

    for record in snapshot.records:
        for intervention in record.interventions:
            if intervention.classroom_intervention_id and intervention.classroom_intervention_id in seen_ci:
                continue
            if intervention.has_followup:
                continue
            if intervention.status not in {InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS}:
                continue
            if intervention.starts_on and intervention.starts_on > today:
                continue
            activity = intervention.template.title if intervention.template_id else skill_label(intervention.skill)
            actions.append(
                TeacherAction(
                    type=ACTION_EVIDENCE_PENDING if intervention.status == InterventionStatus.IN_PROGRESS else ACTION_INTERVENTION_FOLLOWUP,
                    priority=PRIORITY_HIGH if intervention.status == InterventionStatus.IN_PROGRESS else PRIORITY_MEDIUM,
                    classroom_id=snapshot.classroom.pk,
                    classroom_name=snapshot.classroom.name,
                    title=f"Registrar acompanhamento de {first_name(record.student.full_name)}",
                    description=f"Atividade {activity} ainda sem registro.",
                    action_url=reverse("teacher:quick_followup_student", args=[intervention.pk]),
                    skill_id=intervention.skill_id,
                    skill_name=skill_label(intervention.skill),
                    student_ids=[record.student_id],
                    student_names=[record.student.full_name],
                    count=1,
                    reason="Acompanhar o que foi observado na atividade.",
                    why="A intervenção está em andamento e ainda não há registro de acompanhamento.",
                    recommended_action="Registrar agora",
                    extra={"intervention_id": intervention.pk, "student_intervention": True},
                )
            )
    return actions


def _reassessment_actions(snapshot: ClassroomSnapshot) -> list[TeacherAction]:
    actions = []
    for item in suggestions_for_snapshot(snapshot):
        url = reverse("teacher:student", args=[item.student_id]) + "?tab=avaliacoes"
        if item.instrument_id:
            url = reverse("assessment:preview", args=[item.enrollment_id, item.instrument_id])
        actions.append(
            TeacherAction(
                type=ACTION_REASSESSMENT_DUE,
                priority=PRIORITY_HIGH,
                classroom_id=snapshot.classroom.pk,
                classroom_name=snapshot.classroom.name,
                title=f"Pode ser um bom momento para observar {item.skill_name} com {first_name(item.student_name)}",
                description=item.reason,
                action_url=url,
                skill_id=item.skill_id,
                skill_name=item.skill_name,
                student_ids=[item.student_id],
                student_names=[item.student_name],
                count=1,
                reason=item.reason,
                why=item.reason,
                recommended_action="Iniciar observação",
                extra={"intervention_id": item.intervention_id or 0, "instrument_id": item.instrument_id},
            )
        )
    return actions


def _accessibility_notices(snapshot: ClassroomSnapshot, existing: list[TeacherAction]) -> list[TeacherAction]:
    notices = []
    for action in existing:
        notes = action.extra.get("accessibility_notes") or []
        if not notes:
            continue
        alts = [n for n in notes if "alternativa" in n.lower()]
        if not alts:
            continue
        notices.append(
            TeacherAction(
                type=ACTION_ACCESSIBILITY_NOTICE,
                priority=PRIORITY_HIGH if alts else PRIORITY_MEDIUM,
                classroom_id=snapshot.classroom.pk,
                classroom_name=snapshot.classroom.name,
                title="Preparar adaptação de acesso",
                description=alts[0],
                action_url=action.action_url,
                skill_id=action.skill_id,
                skill_name=action.skill_name,
                student_ids=action.student_ids,
                student_names=action.student_names,
                count=len(alts),
                reason=alts[0],
                why="Aviso preventivo de acesso — não indica desempenho.",
                recommended_action="Ver alternativa",
                extra={"intervention_id": action.extra.get("intervention_id", 0)},
            )
        )
    return notices
