"""Student accessibility profile helpers with audit."""
from __future__ import annotations

from django.db import transaction

from apps.accessibility.models import (
    AccessibilityFeature,
    StudentAccessibilityFeature,
    StudentAccessibilityProfile,
)
from apps.core.services.audit import log_action
from apps.students.models import Student


def get_or_create_profile(student: Student) -> StudentAccessibilityProfile:
    profile, _ = StudentAccessibilityProfile.objects.get_or_create(student=student)
    return profile


@transaction.atomic
def set_student_features(
    *,
    student: Student,
    feature_codes: list[str],
    actor=None,
    notes: str = "",
) -> StudentAccessibilityProfile:
    profile = get_or_create_profile(student)
    if notes:
        profile.notes = notes
    profile.updated_by = actor if getattr(actor, "is_authenticated", False) else None
    profile.save()

    features = list(AccessibilityFeature.objects.filter(code__in=feature_codes, is_active=True))
    keep_ids = set()
    for i, feature in enumerate(features):
        link, _ = StudentAccessibilityFeature.objects.update_or_create(
            profile=profile,
            feature=feature,
            defaults={"is_active": True, "priority": i},
        )
        keep_ids.add(link.pk)

    StudentAccessibilityFeature.objects.filter(profile=profile).exclude(pk__in=keep_ids).update(is_active=False)

    log_action(
        actor=actor,
        action="update",
        object_type="StudentAccessibilityProfile",
        object_id=profile.pk,
        message="Atualização de recursos de acessibilidade",
        payload={"student_id": student.pk, "features": feature_codes},
    )
    return profile
