"""School year lifecycle — never mutate historical enrollments."""
from __future__ import annotations

from django.db import transaction

from apps.core.services.audit import log_action
from apps.schools.models import Classroom, SchoolYear
from apps.students.models import Enrollment


@transaction.atomic
def activate_school_year(year: SchoolYear, *, actor=None) -> SchoolYear:
    year.is_active = True
    year.save()
    log_action(
        actor=actor,
        action="update",
        object_type="SchoolYear",
        object_id=year.pk,
        message=f"Ano letivo {year.year} ativado",
    )
    return year


@transaction.atomic
def enroll_student_in_new_year(*, student, classroom: Classroom, actor=None) -> Enrollment:
    """Create a new enrollment for a new year; leave previous enrollments intact."""
    if classroom.school_year.is_active is False:
        # still allowed — admin may prepare next year
        pass
    previous = Enrollment.objects.filter(student=student, school_year=classroom.school_year).first()
    if previous:
        previous.classroom = classroom
        previous.status = Enrollment.Status.ACTIVE
        previous.is_active = True
        previous.save()
        enrollment = previous
    else:
        # Close active enrollments of other years as completed (soft), without deleting
        Enrollment.objects.filter(student=student, status=Enrollment.Status.ACTIVE).exclude(
            school_year=classroom.school_year
        ).update(status=Enrollment.Status.COMPLETED)
        enrollment = Enrollment.objects.create(
            student=student,
            classroom=classroom,
            school_year=classroom.school_year,
            status=Enrollment.Status.ACTIVE,
        )
    log_action(
        actor=actor,
        action="enrollment",
        object_type="Enrollment",
        object_id=enrollment.pk,
        message=f"Matrícula {student} em {classroom}",
    )
    return enrollment
