"""Shared report payloads — HTML and PDF consume the same numbers."""
from __future__ import annotations

from urllib.parse import urlencode

from apps.accessibility.permissions import active_resource_labels_for_teacher
from apps.analytics.models import AggregatedIndicator, StudentSkillStatus
from apps.analytics.services.accessibility_indicators import network_accessibility_stats
from apps.assessments.models import AssessmentSession
from apps.curriculum.models import Skill
from apps.evidences.models import Evidence
from apps.interventions.models import ClassroomIntervention, StudentIntervention
from apps.schools.models import Municipality, School, SchoolYear
from apps.students.models import Enrollment, Student


def student_report_data(student: Student) -> dict:
    enrollment = student.current_enrollment()
    statuses = list(StudentSkillStatus.objects.filter(student=student).select_related("skill", "last_session"))
    sessions = list(
        AssessmentSession.objects.filter(enrollment__student=student)
        .select_related("instrument", "instrument__skill")
        .order_by("-started_at")
    )
    evidences = list(
        Evidence.objects.filter(student=student, is_active=True).select_related("skill")[:30]
    )
    interventions = list(
        StudentIntervention.objects.filter(student=student, is_active=True).select_related("skill")
    )
    trajectory = list(
        student.enrollments.filter(is_active=True)
        .select_related("classroom", "school_year", "classroom__school")
        .order_by("-school_year__year")
    )
    attention = [s for s in statuses if s.needs_attention]
    return {
        "student": student,
        "enrollment": enrollment,
        "trajectory": trajectory,
        "statuses": statuses,
        "sessions": sessions,
        "evidences": evidences,
        "interventions": interventions,
        "resource_labels": active_resource_labels_for_teacher(student),
        "attention_count": len(attention),
        "completed_sessions": sum(
            1 for s in sessions if s.status == AssessmentSession.Status.COMPLETED
        ),
        "adapted_sessions": sum(1 for s in sessions if s.application_mode == "adapted" or s.active_features),
    }


def classroom_report_data(classroom) -> dict:
    enrollments = list(
        classroom.enrollments.filter(is_active=True).select_related("student").order_by("student__full_name")
    )
    student_ids = [e.student_id for e in enrollments]
    statuses = list(
        StudentSkillStatus.objects.filter(student_id__in=student_ids).select_related("skill", "student")
    )
    by_student: dict[int, list] = {}
    for status in statuses:
        by_student.setdefault(status.student_id, []).append(status)

    rows = []
    attention = pending = ok = 0
    for enrollment in enrollments:
        st = by_student.get(enrollment.student_id, [])
        needs = any(s.needs_attention for s in st)
        has_completed = AssessmentSession.objects.filter(
            enrollment=enrollment, status=AssessmentSession.Status.COMPLETED
        ).exists()
        if needs:
            badge, label = "attention", "Atenção"
            attention += 1
        elif has_completed:
            badge, label = "ok", "Acompanhamento regular"
            ok += 1
        else:
            badge, label = "pending", "Sondagem pendente"
            pending += 1
        rows.append(
            {
                "enrollment": enrollment,
                "student": enrollment.student,
                "badge": badge,
                "label": label,
                "statuses": st,
            }
        )

    skill_attention = {}
    for status in statuses:
        if status.needs_attention:
            skill_attention[status.skill.name] = skill_attention.get(status.skill.name, 0) + 1

    class_ints = list(
        ClassroomIntervention.objects.filter(classroom=classroom, is_active=True).select_related("skill")
    )
    return {
        "classroom": classroom,
        "enrollments": enrollments,
        "rows": rows,
        "total": len(enrollments),
        "attention": attention,
        "pending": pending,
        "ok": ok,
        "skill_attention": sorted(skill_attention.items(), key=lambda x: -x[1]),
        "classroom_interventions": class_ints,
        "coverage": round(100 * ok / len(enrollments), 1) if enrollments else 0,
    }


def school_report_data(school, year=None, classroom=None, skill=None) -> dict:
    year = year or SchoolYear.objects.filter(is_active=True).first()
    classrooms = school.classrooms.filter(is_active=True, school_year=year) if year else school.classrooms.none()
    if classroom:
        enrollments = Enrollment.objects.filter(classroom=classroom, is_active=True)
        classrooms_count = 1
    else:
        enrollments = Enrollment.objects.filter(classroom__in=classrooms, is_active=True)
        classrooms_count = classrooms.count()
    students = Student.objects.filter(enrollments__in=enrollments).distinct()
    statuses = StudentSkillStatus.objects.filter(enrollment__in=enrollments)
    if skill:
        statuses = statuses.filter(skill=skill)

    school_indicators = list(
        AggregatedIndicator.objects.filter(
            school=school,
            school_year=year,
            scope=AggregatedIndicator.Scope.SCHOOL,
            metric_key="attention_pct",
            skill__isnull=False,
        )
        .select_related("skill")
        .order_by("skill__name")
    )
    classroom_indicators = list(
        AggregatedIndicator.objects.filter(
            school=school,
            school_year=year,
            scope=AggregatedIndicator.Scope.CLASSROOM,
            metric_key="attention_pct",
            skill__isnull=False,
        )
        .select_related("skill", "classroom")
        .order_by("classroom__name", "skill__name")
    )
    if classroom:
        classroom_indicators = [i for i in classroom_indicators if i.classroom_id == classroom.pk]
        school_indicators = []
    if skill:
        school_indicators = [i for i in school_indicators if i.skill_id == skill.pk]
        classroom_indicators = [i for i in classroom_indicators if i.skill_id == skill.pk]

    attention_students = statuses.filter(needs_attention=True).values("student_id").distinct().count()
    session_qs = AssessmentSession.objects.filter(
        enrollment__in=enrollments,
        status=AssessmentSession.Status.COMPLETED,
        is_active=True,
    )
    if skill:
        session_qs = session_qs.filter(instrument__skill=skill)
    assessed = session_qs.values("enrollment_id").distinct().count()
    total = enrollments.count()
    query = {}
    if year:
        query["ano"] = str(year.pk)
    if classroom:
        query["turma"] = str(classroom.pk)
    if skill:
        query["habilidade"] = str(skill.pk)
    return {
        "school": school,
        "year": year,
        "classroom": classroom,
        "skill": skill,
        "classrooms": classrooms.order_by("name"),
        "skills": Skill.objects.filter(
            pk__in=StudentSkillStatus.objects.filter(
                enrollment__classroom__school=school,
                enrollment__school_year=year,
            ).values_list("skill_id", flat=True)
        ).order_by("name")
        if year
        else Skill.objects.none(),
        "years": SchoolYear.objects.all().order_by("-year"),
        "filter_qs": urlencode(query),
        "scope_label": " · ".join(
            p
            for p in [
                str(year) if year else "",
                classroom.name if classroom else "Todas as turmas",
                skill.name if skill else "",
            ]
            if p
        ),
        "classrooms_count": classrooms_count,
        "students_count": students.count(),
        "attention_students": attention_students,
        "coverage": round(100 * assessed / total, 1) if total else 0,
        "school_indicators": school_indicators,
        "classroom_indicators": classroom_indicators,
        "indicators": school_indicators + classroom_indicators,
    }


def network_report_data(municipality=None, year=None) -> dict:
    municipality = municipality or Municipality.objects.first()
    year = year or SchoolYear.objects.filter(is_active=True).first()
    schools = School.objects.filter(is_active=True)
    if municipality:
        schools = schools.filter(municipality=municipality)
    indicators = list(
        AggregatedIndicator.objects.filter(scope=AggregatedIndicator.Scope.NETWORK, school_year=year)
        .select_related("skill")
        .order_by("metric_key", "-metric_value")
    )
    total_enrollments = Enrollment.objects.filter(school_year=year, is_active=True).count() if year else 0
    assessed = (
        AssessmentSession.objects.filter(
            status=AssessmentSession.Status.COMPLETED,
            enrollment__school_year=year,
        )
        .values("enrollment_id")
        .distinct()
        .count()
        if year
        else 0
    )
    return {
        "municipality": municipality,
        "year": year,
        "schools_count": schools.count(),
        "students_count": Student.objects.filter(
            is_active=True, enrollments__classroom__school__in=schools, enrollments__is_active=True
        )
        .distinct()
        .count(),
        "coverage": round(100 * assessed / total_enrollments, 1) if total_enrollments else 0,
        "indicators": indicators,
        "a11y_stats": network_accessibility_stats(school_year=year),
    }
