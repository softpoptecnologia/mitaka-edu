"""Scoped query selectors by user role."""
from __future__ import annotations

from django.db.models import QuerySet

from apps.accounts.models import Role
from apps.core.permissions import user_role_code
from apps.schools.models import Classroom, School
from apps.students.models import Enrollment, Student


def schools_for_user(user, *, include_inactive: bool = False) -> QuerySet[School]:
    qs = School.objects.select_related("municipality")
    if not include_inactive:
        qs = qs.filter(is_active=True)
    code = user_role_code(user)
    if code in (Role.Code.SUPERADMIN, Role.Code.SECRETARIA, Role.Code.TECNICO):
        return qs
    profile = user.profile
    if profile and profile.school_id:
        return qs.filter(pk=profile.school_id)
    return qs.none()


def classrooms_for_user(user, *, include_inactive: bool = False) -> QuerySet[Classroom]:
    qs = Classroom.objects.select_related("school", "school_year")
    if not include_inactive:
        qs = qs.filter(is_active=True)
    code = user_role_code(user)
    if code in (Role.Code.SUPERADMIN, Role.Code.SECRETARIA, Role.Code.TECNICO):
        return qs
    if code in (Role.Code.GESTOR, Role.Code.COORDENADOR, Role.Code.AEE):
        profile = user.profile
        if profile and profile.school_id:
            return qs.filter(school_id=profile.school_id)
        return qs.none()
    if code == Role.Code.PROFESSOR:
        return qs.filter(teacher_links__teacher=user).distinct()
    return qs.none()


def students_for_user(user, *, include_inactive: bool = False) -> QuerySet[Student]:
    classroom_ids = classrooms_for_user(user, include_inactive=include_inactive).values_list("id", flat=True)
    qs = Student.objects.filter(enrollments__classroom_id__in=classroom_ids)
    if not include_inactive:
        qs = qs.filter(is_active=True, enrollments__is_active=True)
    return qs.distinct().order_by("full_name")


def enrollments_for_user(user, *, include_inactive: bool = False) -> QuerySet[Enrollment]:
    classroom_ids = classrooms_for_user(user, include_inactive=include_inactive).values_list("id", flat=True)
    qs = Enrollment.objects.filter(classroom_id__in=classroom_ids).select_related(
        "student", "classroom", "school_year", "classroom__school"
    )
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return qs


def user_can_access_classroom(user, classroom: Classroom, *, include_inactive: bool = False) -> bool:
    return classrooms_for_user(user, include_inactive=include_inactive).filter(pk=classroom.pk).exists()


def user_can_access_student(user, student: Student, *, include_inactive: bool = False) -> bool:
    return students_for_user(user, include_inactive=include_inactive).filter(pk=student.pk).exists()


def user_can_access_enrollment(user, enrollment: Enrollment, *, include_inactive: bool = False) -> bool:
    return enrollments_for_user(user, include_inactive=include_inactive).filter(pk=enrollment.pk).exists()
