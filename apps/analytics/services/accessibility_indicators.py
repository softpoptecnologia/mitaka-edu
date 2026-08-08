"""Administrative accessibility indicators — never individual clinical labels."""
from __future__ import annotations

from apps.assessments.models import AssessmentItem, AssessmentItemVariant, AssessmentResponse, AssessmentSession


def network_accessibility_stats(
    school_year=None,
    school=None,
    classroom=None,
    enrollment_ids=None,
) -> dict:
    sessions = AssessmentSession.objects.all()
    if enrollment_ids is not None:
        sessions = sessions.filter(enrollment_id__in=list(enrollment_ids))
    else:
        if school_year:
            sessions = sessions.filter(enrollment__school_year=school_year)
        if classroom:
            sessions = sessions.filter(enrollment__classroom=classroom)
        elif school:
            sessions = sessions.filter(enrollment__classroom__school=school)

    sessions_adapted = sessions.filter(application_mode=AssessmentSession.ApplicationMode.ADAPTED).count()
    sessions_with_features = sessions.exclude(active_features=[]).count()
    total_items = AssessmentItem.objects.count()
    items_with_variant = (
        AssessmentItem.objects.filter(
            variants__pedagogical_approval_status__in=[
                AssessmentItemVariant.ApprovalStatus.APPROVED,
                AssessmentItemVariant.ApprovalStatus.PUBLISHED,
            ],
            variants__active=True,
        )
        .distinct()
        .count()
    )
    blocked_qs = AssessmentResponse.objects.filter(
        equivalence_applied__in=[
            AssessmentResponse.EquivalenceApplied.REQUIRES_ALTERNATIVE,
            AssessmentResponse.EquivalenceApplied.BLOCKED,
        ]
    )
    if enrollment_ids is not None:
        blocked_qs = blocked_qs.filter(session__enrollment_id__in=list(enrollment_ids))
    else:
        if school_year:
            blocked_qs = blocked_qs.filter(session__enrollment__school_year=school_year)
        if classroom:
            blocked_qs = blocked_qs.filter(session__enrollment__classroom=classroom)
        elif school:
            blocked_qs = blocked_qs.filter(session__enrollment__classroom__school=school)
    blocked = blocked_qs.count()
    coverage_pct = round(100.0 * items_with_variant / total_items, 1) if total_items else 0.0
    return {
        "sessions_with_accessibility": sessions_with_features,
        "sessions_adapted": sessions_adapted,
        "variant_coverage_pct": coverage_pct,
        "items_with_published_variant": items_with_variant,
        "total_items": total_items,
        "accessibility_blocks": blocked,
    }
