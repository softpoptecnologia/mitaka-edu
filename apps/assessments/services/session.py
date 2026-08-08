"""Assessment session lifecycle, adaptive assembly and autosave."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.assessments.models import (
    AssessmentInstrument,
    AssessmentResponse,
    AssessmentSession,
)
from apps.assessments.services.resolver import AccessibilityAssessmentResolver
from apps.assessments.services.scoring import score_session
from apps.students.models import Enrollment


@transaction.atomic
def start_session(*, enrollment: Enrollment, instrument: AssessmentInstrument, started_by) -> AssessmentSession:
    existing = (
        AssessmentSession.objects.filter(
            enrollment=enrollment,
            instrument=instrument,
            status=AssessmentSession.Status.IN_PROGRESS,
            is_active=True,
        )
        .order_by("-started_at")
        .first()
    )
    if existing:
        return existing

    resolver = AccessibilityAssessmentResolver()
    plan = resolver.resolve_instrument(student=enrollment.student, instrument=instrument)
    mode = AssessmentSession.ApplicationMode.STANDARD
    if plan.active_features or plan.equivalent_count or plan.alternative_count:
        mode = AssessmentSession.ApplicationMode.ADAPTED
    if instrument.instrument_type == AssessmentInstrument.InstrumentType.OBSERVATIONAL:
        mode = AssessmentSession.ApplicationMode.OBSERVATIONAL

    return AssessmentSession.objects.create(
        enrollment=enrollment,
        instrument=instrument,
        matrix_version=instrument.matrix_version,
        started_by=started_by,
        status=AssessmentSession.Status.IN_PROGRESS,
        current_item_order=0,
        application_mode=mode,
        active_features=plan.active_features,
        adaptation_summary=plan.summary_dict(),
    )


@transaction.atomic
def save_response(
    *,
    session: AssessmentSession,
    item,
    option=None,
    text_value: str = "",
    applied_by=None,
    is_observational: bool = False,
    instruction_repeats: int = 0,
    response_time_seconds: int | None = None,
    mark_not_applicable: bool = False,
) -> AssessmentResponse:
    if session.status != AssessmentSession.Status.IN_PROGRESS:
        raise ValueError("Sessão não está em andamento.")

    resolver = AccessibilityAssessmentResolver()
    resolved = resolver.resolve_item(student=session.enrollment.student, assessment_item=item)

    if mark_not_applicable or resolved.equivalence in {
        AssessmentResponse.EquivalenceApplied.REQUIRES_ALTERNATIVE,
        AssessmentResponse.EquivalenceApplied.BLOCKED,
        AssessmentResponse.EquivalenceApplied.NOT_APPLICABLE,
    }:
        equivalence = (
            AssessmentResponse.EquivalenceApplied.NOT_APPLICABLE
            if mark_not_applicable
            else resolved.equivalence
        )
        score = 0
        counts = False
        option = None
        text_value = text_value or resolved.reason
    else:
        equivalence = resolved.equivalence
        score = option.score_value if option else 0
        counts = True

    # Access accommodations never reduce score by themselves
    variant = resolved.variant
    response, _ = AssessmentResponse.objects.update_or_create(
        session=session,
        item=item,
        defaults={
            "option": option,
            "text_value": text_value,
            "score_value": score if counts else 0,
            "original_item": item,
            "variant_used": variant,
            "variant_version": variant.version if variant else None,
            "variant_name_snapshot": variant.name if variant else "",
            "equivalence_applied": equivalence,
            "active_features_snapshot": list(session.active_features or resolved.active_features),
            "is_observational": is_observational
            or session.application_mode == AssessmentSession.ApplicationMode.OBSERVATIONAL,
            "applied_by": applied_by,
            "counts_toward_score": counts,
            "instruction_repeats": instruction_repeats,
            "response_time_seconds": response_time_seconds,
        },
    )
    items = list(session.instrument.items.order_by("order", "id"))
    try:
        idx = next(i for i, it in enumerate(items) if it.pk == item.pk)
        session.current_item_order = min(idx + 1, len(items))
        session.save(update_fields=["current_item_order", "updated_at"])
    except StopIteration:
        pass
    return response


@transaction.atomic
def complete_session(session: AssessmentSession, *, force_status: str | None = None):
    terminal = {
        AssessmentSession.Status.COMPLETED,
        AssessmentSession.Status.PARTIALLY_COMPLETED,
        AssessmentSession.Status.NOT_APPLICABLE,
        AssessmentSession.Status.REQUIRES_ALTERNATIVE_INSTRUMENT,
        AssessmentSession.Status.ACCESSIBILITY_BLOCKED,
    }
    if session.status in terminal and session.status != AssessmentSession.Status.IN_PROGRESS:
        if session.status == AssessmentSession.Status.COMPLETED:
            return session

    responses = list(session.responses.all())
    total_items = session.instrument.items.count()
    scored = [r for r in responses if r.counts_toward_score]
    blocked = [
        r
        for r in responses
        if r.equivalence_applied
        in {
            AssessmentResponse.EquivalenceApplied.REQUIRES_ALTERNATIVE,
            AssessmentResponse.EquivalenceApplied.BLOCKED,
        }
    ]
    na = [
        r
        for r in responses
        if r.equivalence_applied == AssessmentResponse.EquivalenceApplied.NOT_APPLICABLE
    ]

    if force_status:
        session.status = force_status
    elif total_items and len(blocked) == total_items:
        session.status = AssessmentSession.Status.REQUIRES_ALTERNATIVE_INSTRUMENT
    elif total_items and len(na) == total_items:
        session.status = AssessmentSession.Status.NOT_APPLICABLE
    elif responses and len(scored) < total_items and (blocked or na):
        session.status = AssessmentSession.Status.PARTIALLY_COMPLETED
    else:
        session.status = AssessmentSession.Status.COMPLETED

    session.completed_at = timezone.now()
    if session.started_at:
        session.duration_seconds = int((session.completed_at - session.started_at).total_seconds())
    session.save(update_fields=["status", "completed_at", "duration_seconds", "updated_at"])

    # Never score pure accessibility blocks as low performance
    if session.status not in {
        AssessmentSession.Status.REQUIRES_ALTERNATIVE_INSTRUMENT,
        AssessmentSession.Status.ACCESSIBILITY_BLOCKED,
        AssessmentSession.Status.NOT_APPLICABLE,
    }:
        score_session(session)
    return session


def preview_adapted_assessment(*, student, instrument) -> dict:
    from apps.accessibility.models import AccessibilityFeature

    plan = AccessibilityAssessmentResolver().resolve_instrument(student=student, instrument=instrument)
    feature_names = list(
        AccessibilityFeature.objects.filter(code__in=plan.active_features).values_list("name", flat=True)
    )
    return {
        "plan": plan,
        "feature_names": feature_names,
        "summary": plan.summary_dict(),
    }
