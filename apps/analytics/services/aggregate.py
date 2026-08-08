"""Refresh aggregated indicators after assessment completion."""
from __future__ import annotations

from django.db.models import Count, Q

from apps.analytics.models import AggregatedIndicator, StudentSkillStatus
from apps.assessments.models import AssessmentSession
from apps.students.models import Enrollment


def refresh_indicators_for_session(session: AssessmentSession) -> None:
    enrollment = session.enrollment
    classroom = enrollment.classroom
    school = classroom.school
    year = enrollment.school_year
    skill = session.instrument.skill
    municipality = school.municipality

    _upsert_classroom_skill(classroom, year, skill)
    _upsert_school_skill(school, year, skill, municipality)
    _upsert_network_skill(municipality, year, skill)
    _upsert_coverage(classroom, school, municipality, year)


def _attention_ratio(enrollment_ids, skill) -> tuple[float, int]:
    statuses = StudentSkillStatus.objects.filter(enrollment_id__in=enrollment_ids, skill=skill)
    total = statuses.count()
    if not total:
        return 0.0, 0
    attention = statuses.filter(needs_attention=True).count()
    return round(100.0 * attention / total, 1), total


def _upsert_classroom_skill(classroom, year, skill):
    lookup = dict(
        scope=AggregatedIndicator.Scope.CLASSROOM,
        school_year=year,
        classroom=classroom,
        school=classroom.school,
        municipality=classroom.school.municipality,
        skill=skill,
        metric_key="attention_pct",
    )
    enrollment_ids = Enrollment.objects.filter(classroom=classroom, is_active=True).values_list("id", flat=True)
    value, sample = _attention_ratio(enrollment_ids, skill)
    if not sample:
        AggregatedIndicator.objects.filter(**lookup).delete()
        return
    AggregatedIndicator.objects.update_or_create(
        **lookup,
        defaults={"metric_value": value, "sample_size": sample, "payload": {"skill": skill.code}},
    )


def _upsert_school_skill(school, year, skill, municipality):
    lookup = dict(
        scope=AggregatedIndicator.Scope.SCHOOL,
        school_year=year,
        school=school,
        municipality=municipality,
        classroom=None,
        skill=skill,
        metric_key="attention_pct",
    )
    enrollment_ids = Enrollment.objects.filter(classroom__school=school, school_year=year, is_active=True).values_list(
        "id", flat=True
    )
    value, sample = _attention_ratio(enrollment_ids, skill)
    if not sample:
        AggregatedIndicator.objects.filter(**lookup).delete()
        return
    AggregatedIndicator.objects.update_or_create(
        **lookup,
        defaults={"metric_value": value, "sample_size": sample, "payload": {"skill": skill.code}},
    )


def _upsert_network_skill(municipality, year, skill):
    lookup = dict(
        scope=AggregatedIndicator.Scope.NETWORK,
        school_year=year,
        municipality=municipality,
        school=None,
        classroom=None,
        skill=skill,
        metric_key="attention_pct",
    )
    enrollment_ids = Enrollment.objects.filter(
        classroom__school__municipality=municipality, school_year=year, is_active=True
    ).values_list("id", flat=True)
    value, sample = _attention_ratio(enrollment_ids, skill)
    if not sample:
        AggregatedIndicator.objects.filter(**lookup).delete()
        return
    AggregatedIndicator.objects.update_or_create(
        **lookup,
        defaults={"metric_value": value, "sample_size": sample, "payload": {"skill": skill.code}},
    )


def _upsert_coverage(classroom, school, municipality, year):
    total = Enrollment.objects.filter(classroom__school__municipality=municipality, school_year=year, is_active=True).count()
    assessed = (
        AssessmentSession.objects.filter(
            enrollment__classroom__school__municipality=municipality,
            enrollment__school_year=year,
            status=AssessmentSession.Status.COMPLETED,
            is_active=True,
        )
        .values("enrollment_id")
        .distinct()
        .count()
    )
    pct = round(100.0 * assessed / total, 1) if total else 0
    AggregatedIndicator.objects.update_or_create(
        scope=AggregatedIndicator.Scope.NETWORK,
        school_year=year,
        municipality=municipality,
        school=None,
        classroom=None,
        skill=None,
        metric_key="assessment_coverage_pct",
        defaults={"metric_value": pct, "sample_size": total, "payload": {"assessed": assessed}},
    )


def rebuild_attention_indicators(school_year) -> None:
    """Recalcula turma/escola/rede a partir dos status atuais — garante nexo no demo e nos relatórios."""
    from apps.curriculum.models import Skill
    from apps.schools.models import Classroom, Municipality, School

    enrollments = Enrollment.objects.filter(school_year=school_year, is_active=True)
    skill_ids = list(
        StudentSkillStatus.objects.filter(enrollment__in=enrollments).values_list("skill_id", flat=True).distinct()
    )
    skills = list(Skill.objects.filter(pk__in=skill_ids))
    classrooms = Classroom.objects.filter(school_year=school_year, is_active=True).select_related("school", "school__municipality")
    for classroom in classrooms:
        for skill in skills:
            _upsert_classroom_skill(classroom, school_year, skill)
    schools = School.objects.filter(is_active=True, classrooms__school_year=school_year).distinct().select_related("municipality")
    for school in schools:
        for skill in skills:
            _upsert_school_skill(school, school_year, skill, school.municipality)
        first_room = next((c for c in classrooms if c.school_id == school.pk), None)
        if first_room:
            _upsert_coverage(first_room, school, school.municipality, school_year)
    for municipality in Municipality.objects.all():
        for skill in skills:
            _upsert_network_skill(municipality, school_year, skill)


def network_skill_needs(municipality=None, school_year=None):
    qs = AggregatedIndicator.objects.filter(
        scope=AggregatedIndicator.Scope.NETWORK,
        metric_key="attention_pct",
        skill__isnull=False,
    ).select_related("skill")
    if municipality:
        qs = qs.filter(municipality=municipality)
    if school_year:
        qs = qs.filter(school_year=school_year)
    return qs.order_by("-metric_value")
