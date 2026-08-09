"""Prefetched classroom snapshot for teacher operational screens."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from apps.accounts.selectors import classrooms_for_user
from apps.analytics.models import StudentSkillStatus
from apps.assessments.models import AssessmentInstrument, AssessmentSession
from apps.interventions.models import ClassroomIntervention, InterventionTemplate, StudentIntervention
from apps.schools.models import Classroom
from apps.students.models import Enrollment


@dataclass
class EnrollmentRecord:
    enrollment: Enrollment
    student: object
    statuses: list = field(default_factory=list)
    statuses_by_skill_id: dict = field(default_factory=dict)
    completed_sessions: list = field(default_factory=list)
    completed_skill_ids: set = field(default_factory=set)
    last_session_by_skill_id: dict = field(default_factory=dict)
    interventions: list = field(default_factory=list)
    feature_codes: list = field(default_factory=list)
    feature_names: list = field(default_factory=list)

    @property
    def student_id(self) -> int:
        return self.student.pk

    @property
    def needs_attention(self) -> bool:
        return any(s.needs_attention for s in self.statuses)

    @property
    def has_completed_session(self) -> bool:
        return bool(self.completed_sessions)

    def status_for(self, skill_id: int):
        return self.statuses_by_skill_id.get(skill_id)

    def active_intervention_for(self, skill_id: int):
        from apps.interventions.models import InterventionStatus

        open_statuses = {InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS}
        for intervention in self.interventions:
            if intervention.skill_id == skill_id and intervention.status in open_statuses:
                return intervention
        return None


@dataclass
class ClassroomSnapshot:
    classroom: Classroom
    records: list[EnrollmentRecord] = field(default_factory=list)
    records_by_student_id: dict = field(default_factory=dict)
    classroom_interventions: list = field(default_factory=list)
    templates_by_skill_id: dict = field(default_factory=dict)
    instruments_by_skill_id: dict = field(default_factory=dict)

    @property
    def enrollment_count(self) -> int:
        return len(self.records)

    def summary_counts(self) -> dict:
        ok = pending = attention = acesso = 0
        for record in self.records:
            if record.feature_codes:
                acesso += 1
            if record.needs_attention:
                attention += 1
            elif record.has_completed_session:
                ok += 1
            else:
                pending += 1
        return {
            "ok": ok,
            "pending": pending,
            "attention": attention,
            "acesso": acesso,
            "total": self.enrollment_count,
        }


def load_snapshots_for_user(user) -> list[ClassroomSnapshot]:
    classrooms = list(
        classrooms_for_user(user)
        .filter(school_year__is_active=True)
        .select_related("school", "school_year")
        .order_by("school__name", "name")
    )
    return load_snapshots_for_classrooms(classrooms)


def load_classroom_snapshot(classroom: Classroom) -> ClassroomSnapshot:
    snapshots = load_snapshots_for_classrooms([classroom])
    return snapshots[0] if snapshots else ClassroomSnapshot(classroom=classroom)


def load_snapshots_for_classrooms(classrooms: list[Classroom]) -> list[ClassroomSnapshot]:
    if not classrooms:
        return []
    classroom_ids = [c.pk for c in classrooms]
    enrollments = list(
        Enrollment.objects.filter(
            classroom_id__in=classroom_ids,
            is_active=True,
            status=Enrollment.Status.ACTIVE,
        )
        .select_related("student", "classroom", "school_year", "classroom__school")
        .prefetch_related(
            "student__accessibility_profile__feature_links__feature",
        )
        .order_by("student__full_name")
    )
    student_ids = [e.student_id for e in enrollments]
    enrollment_ids = [e.pk for e in enrollments]

    statuses = list(
        StudentSkillStatus.objects.filter(student_id__in=student_ids)
        .select_related("skill", "skill__dimension", "last_session")
        .order_by("skill__dimension__order", "skill__name")
    )
    statuses_by_student: dict[int, list] = defaultdict(list)
    for status in statuses:
        statuses_by_student[status.student_id].append(status)

    sessions = list(
        AssessmentSession.objects.filter(enrollment_id__in=enrollment_ids, is_active=True)
        .select_related("instrument", "instrument__skill")
        .order_by("-started_at")
    )
    sessions_by_enrollment: dict[int, list] = defaultdict(list)
    for session in sessions:
        sessions_by_enrollment[session.enrollment_id].append(session)

    interventions = list(
        StudentIntervention.objects.filter(enrollment_id__in=enrollment_ids, is_active=True)
        .select_related("skill", "skill__dimension", "template", "classroom_intervention", "responsible")
        .order_by("-starts_on", "-created_at")
    )
    interventions_by_student: dict[int, list] = defaultdict(list)
    for intervention in interventions:
        interventions_by_student[intervention.student_id].append(intervention)

    classroom_interventions = list(
        ClassroomIntervention.objects.filter(classroom_id__in=classroom_ids, is_active=True)
        .select_related("skill", "skill__dimension", "template", "responsible")
        .order_by("-starts_on", "-created_at")
    )
    ci_by_classroom: dict[int, list] = defaultdict(list)
    for item in classroom_interventions:
        ci_by_classroom[item.classroom_id].append(item)

    templates = list(
        InterventionTemplate.objects.filter(is_active=True).select_related("skill", "skill__dimension")
    )
    templates_by_skill = {}
    for template in templates:
        templates_by_skill.setdefault(template.skill_id, template)

    instruments = list(
        AssessmentInstrument.objects.filter(is_active=True, is_published=True).select_related(
            "skill", "skill__dimension"
        )
    )
    instruments_by_skill: dict[int, list] = defaultdict(list)
    for instrument in instruments:
        instruments_by_skill[instrument.skill_id].append(instrument)

    snapshots = []
    enrollments_by_classroom: dict[int, list] = defaultdict(list)
    for enrollment in enrollments:
        enrollments_by_classroom[enrollment.classroom_id].append(enrollment)

    for classroom in classrooms:
        records = []
        for enrollment in enrollments_by_classroom.get(classroom.pk, []):
            student = enrollment.student
            student_statuses = statuses_by_student.get(student.pk, [])
            completed = [
                s
                for s in sessions_by_enrollment.get(enrollment.pk, [])
                if s.status == AssessmentSession.Status.COMPLETED
            ]
            last_by_skill = {}
            completed_skill_ids = set()
            for session in completed:
                skill_id = session.instrument.skill_id
                completed_skill_ids.add(skill_id)
                last_by_skill.setdefault(skill_id, session)
            feature_codes, feature_names = _feature_payload(student)
            record = EnrollmentRecord(
                enrollment=enrollment,
                student=student,
                statuses=student_statuses,
                statuses_by_skill_id={s.skill_id: s for s in student_statuses},
                completed_sessions=completed,
                completed_skill_ids=completed_skill_ids,
                last_session_by_skill_id=last_by_skill,
                interventions=interventions_by_student.get(student.pk, []),
                feature_codes=feature_codes,
                feature_names=feature_names,
            )
            records.append(record)
        snapshot = ClassroomSnapshot(
            classroom=classroom,
            records=records,
            records_by_student_id={r.student_id: r for r in records},
            classroom_interventions=ci_by_classroom.get(classroom.pk, []),
            templates_by_skill_id=templates_by_skill,
            instruments_by_skill_id=dict(instruments_by_skill),
        )
        snapshots.append(snapshot)
    return snapshots


def _feature_payload(student) -> tuple[list[str], list[str]]:
    profile = getattr(student, "accessibility_profile", None)
    if profile is None or not getattr(profile, "is_active", True):
        return [], []
    codes, names = [], []
    for link in profile.feature_links.all():
        if not link.is_active:
            continue
        feature = link.feature
        if not feature.is_active:
            continue
        codes.append(feature.code)
        names.append(feature.name)
    return codes, names
