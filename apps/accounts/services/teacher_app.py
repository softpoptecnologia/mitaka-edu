"""Payload do app Flutter do professor: turmas, alunos, status e acessibilidade."""
from __future__ import annotations

from apps.accounts.selectors import classrooms_for_user
from apps.core.permissions import user_role_code
from apps.interventions.services.snapshot import load_snapshots_for_user


def _profile(user):
    return getattr(user, "userprofile", None)


def teacher_payload(user) -> dict:
    profile = _profile(user)
    school = getattr(profile, "school", None) if profile else None
    return {
        "id": user.pk,
        "username": user.username,
        "display_name": profile.greeting_name if profile else (user.get_full_name() or user.username),
        "role": user_role_code(user),
        "school_name": school.name if school else "",
        "classroom_ids": list(
            classrooms_for_user(user).filter(school_year__is_active=True).values_list("id", flat=True)
        ),
    }


def _student_status(record) -> str:
    if record.needs_attention:
        return "attention"
    if record.has_completed_session:
        return "ok"
    return "pending"


def _support_notes(student) -> str:
    profile = getattr(student, "accessibility_profile", None)
    if profile is None or not getattr(profile, "is_active", True):
        return ""
    return (profile.notes or "").strip()


def serialize_classroom_snapshot(snapshot) -> dict:
    classroom = snapshot.classroom
    return {
        "id": classroom.pk,
        "name": classroom.name,
        "grade": classroom.grade_label,
        "school_name": classroom.school.name,
        "summary": snapshot.summary_counts(),
        "students": [
            {
                "id": record.student_id,
                "enrollment_id": record.enrollment.pk,
                "full_name": record.student.full_name,
                "status": _student_status(record),
                "feature_codes": list(record.feature_codes),
                "feature_names": list(record.feature_names),
                "support_notes": _support_notes(record.student),
            }
            for record in snapshot.records
        ],
    }


def bootstrap_payload(user) -> dict:
    snapshots = load_snapshots_for_user(user)
    return {
        "teacher": teacher_payload(user),
        "classrooms": [serialize_classroom_snapshot(snap) for snap in snapshots],
    }
