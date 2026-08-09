"""Temporary pedagogical grouping suggestions within a classroom."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.utils import timezone

from apps.interventions.models import FollowupResult, InterventionStatus
from apps.interventions.services.accessibility_notes import notes_for_students
from apps.interventions.services.labels import first_name, skill_label, template_activity_title
from apps.interventions.services.reassessment import reassessment_days_for
from apps.interventions.services.settings import (
    MAX_GROUP_SIZE,
    MAX_SUGGESTED_GROUPS,
    MIN_GROUP_SIZE,
    RECENT_FOLLOWUP_SUPPRESSION_DAYS,
)


@dataclass
class SuggestedGroup:
    skill_id: int
    skill_name: str
    skill: object | None
    students: list = field(default_factory=list)
    student_ids: list[int] = field(default_factory=list)
    enrollments: list = field(default_factory=list)
    template: object | None = None
    reason: str = ""
    why: str = ""
    accessibility_notes: list[str] = field(default_factory=list)
    alternative_needed: list[str] = field(default_factory=list)
    kind: str = "attention"  # attention | consolidation | individual
    last_observation: object | None = None

    @property
    def size(self) -> int:
        return len(self.student_ids)

    @property
    def activity_title(self) -> str:
        return template_activity_title(self.template)

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "student_ids": self.student_ids,
            "student_names": [s.full_name for s in self.students],
            "template_id": getattr(self.template, "pk", None),
            "template_title": getattr(self.template, "title", None),
            "activity_title": self.activity_title,
            "objective": getattr(self.template, "objective", "") if self.template else "",
            "suggested_minutes": getattr(self.template, "suggested_activity_minutes", None),
            "reason": self.reason,
            "why": self.why,
            "accessibility_notes": self.accessibility_notes,
            "alternative_needed": self.alternative_needed,
            "kind": self.kind,
            "size": self.size,
        }


def _recent_followup_blocks(record, skill_id: int, *, now) -> bool:
    cutoff = now - timedelta(days=RECENT_FOLLOWUP_SUPPRESSION_DAYS)
    for intervention in record.interventions:
        if intervention.skill_id != skill_id:
            continue
        if intervention.status == InterventionStatus.CANCELLED:
            continue
        if intervention.has_followup and intervention.followup_recorded_at and intervention.followup_recorded_at >= cutoff:
            if intervention.followup_result != FollowupResult.NOT_OBSERVED:
                return True
        wait = reassessment_days_for(intervention.followup_result or None)
        reference = intervention.followup_recorded_at or (
            intervention.updated_at if intervention.status == InterventionStatus.COMPLETED else None
        )
        if wait is not None and reference and now >= reference + timedelta(days=wait):
            last_session = record.last_session_by_skill_id.get(skill_id)
            if not last_session or last_session.started_at < reference:
                return True
        if intervention.status in {InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS} and not intervention.has_followup:
            return True
    return False


def _eligible_for_skill(record, skill_id: int, *, now) -> bool:
    status = record.status_for(skill_id)
    if status is None or not status.needs_attention:
        return False
    if _recent_followup_blocks(record, skill_id, now=now):
        return False
    return True


def suggest_groups(snapshot, *, include_consolidation: bool = False) -> list[SuggestedGroup]:
    now = timezone.now()
    by_skill: dict[int, list] = {}
    skill_objs = {}
    for record in snapshot.records:
        for status in record.statuses:
            if not _eligible_for_skill(record, status.skill_id, now=now):
                continue
            by_skill.setdefault(status.skill_id, []).append(record)
            skill_objs[status.skill_id] = status.skill

    ranked = sorted(by_skill.items(), key=lambda item: (-len(item[1]), skill_label(skill_objs[item[0]])))
    groups: list[SuggestedGroup] = []
    for skill_id, records in ranked:
        if len(groups) >= MAX_SUGGESTED_GROUPS:
            break
        skill = skill_objs[skill_id]
        chunks = _split_records(records)
        template = snapshot.templates_by_skill_id.get(skill_id)
        instruments = snapshot.instruments_by_skill_id.get(skill_id) or []
        last_obs = None
        for record in records:
            status = record.status_for(skill_id)
            session = getattr(status, "last_session", None) if status else None
            if session and (last_obs is None or session.started_at > last_obs):
                last_obs = session.started_at
        for index, chunk in enumerate(chunks, start=1):
            if len(groups) >= MAX_SUGGESTED_GROUPS:
                break
            notes, alts = notes_for_students(records=chunk, instruments=instruments)
            names = [first_name(r.student.full_name) for r in chunk]
            label = skill_label(skill)
            kind = "individual" if len(chunk) < MIN_GROUP_SIZE else "attention"
            suffix = f" (grupo {index})" if len(chunks) > 1 else ""
            why_date = last_obs.strftime("%d/%m/%Y") if last_obs else "registros recentes"
            groups.append(
                SuggestedGroup(
                    skill_id=skill_id,
                    skill_name=label,
                    skill=skill,
                    students=[r.student for r in chunk],
                    student_ids=[r.student_id for r in chunk],
                    enrollments=[r.enrollment for r in chunk],
                    template=template,
                    reason=f"{len(chunk)} estudantes precisam trabalhar {label}{suffix}.",
                    why=(
                        f"{len(chunk)} estudantes apresentaram necessidade de maior mediação em {label} "
                        f"nas observações mais recentes. Última observação: {why_date}."
                        + (f" Atividade disponível: {template.title}." if template else "")
                    ),
                    accessibility_notes=notes,
                    alternative_needed=alts,
                    kind=kind,
                    last_observation=last_obs,
                )
            )

    if include_consolidation and groups:
        attention_ids = {sid for group in groups for sid in group.student_ids}
        rest = [r for r in snapshot.records if r.student_id not in attention_ids]
        if rest:
            groups.append(
                SuggestedGroup(
                    skill_id=0,
                    skill_name="Consolidação",
                    skill=None,
                    students=[r.student for r in rest],
                    student_ids=[r.student_id for r in rest],
                    enrollments=[r.enrollment for r in rest],
                    reason="Estudantes que não estão em situação de atenção nesta habilidade.",
                    why="Sugestão de consolidação para quem já acompanha com mais autonomia.",
                    kind="consolidation",
                )
            )
    return groups


def suggest_group_for_skill(snapshot, skill_id: int, *, student_ids: list[int] | None = None) -> SuggestedGroup | None:
    groups = suggest_groups(snapshot, include_consolidation=False)
    for group in groups:
        if group.skill_id == skill_id:
            if student_ids is not None:
                allowed = set(student_ids)
                classroom_ids = {r.student_id for r in snapshot.records}
                keep_ids = [sid for sid in group.student_ids if sid in allowed and sid in classroom_ids]
                extra_ids = [sid for sid in student_ids if sid in classroom_ids and sid not in keep_ids]
                ordered_ids = keep_ids + extra_ids
                records = [snapshot.records_by_student_id[sid] for sid in ordered_ids if sid in snapshot.records_by_student_id]
                if not records:
                    return None
                instruments = snapshot.instruments_by_skill_id.get(skill_id) or []
                notes, alts = notes_for_students(records=records, instruments=instruments)
                group.students = [r.student for r in records]
                group.student_ids = [r.student_id for r in records]
                group.enrollments = [r.enrollment for r in records]
                group.accessibility_notes = notes
                group.alternative_needed = alts
                group.reason = f"{len(records)} estudantes precisam trabalhar {group.skill_name}."
                group.kind = "individual" if len(records) < MIN_GROUP_SIZE else "attention"
            return group
    if student_ids:
        classroom_ids = {r.student_id for r in snapshot.records}
        records = [snapshot.records_by_student_id[sid] for sid in student_ids if sid in classroom_ids]
        if not records:
            return None
        skill = None
        template = snapshot.templates_by_skill_id.get(skill_id)
        for record in records:
            status = record.status_for(skill_id)
            if status:
                skill = status.skill
                break
        if skill is None and template:
            skill = template.skill
        instruments = snapshot.instruments_by_skill_id.get(skill_id) or []
        notes, alts = notes_for_students(records=records, instruments=instruments)
        label = skill_label(skill) if skill else "Habilidade"
        return SuggestedGroup(
            skill_id=skill_id,
            skill_name=label,
            skill=skill,
            students=[r.student for r in records],
            student_ids=[r.student_id for r in records],
            enrollments=[r.enrollment for r in records],
            template=template,
            reason=f"Sugestão para esta turma: trabalhar {label}.",
            why="Grupo ajustado pelo professor a partir da sugestão do Mitaka.",
            accessibility_notes=notes,
            alternative_needed=alts,
            kind="individual" if len(records) < MIN_GROUP_SIZE else "attention",
        )
    return None


def _split_records(records: list) -> list[list]:
    if not records:
        return []
    if len(records) <= MAX_GROUP_SIZE:
        return [records]
    chunks = []
    for i in range(0, len(records), MAX_GROUP_SIZE):
        chunk = records[i : i + MAX_GROUP_SIZE]
        if chunk:
            chunks.append(chunk)
    return chunks
