"""Configurable scoring — accessibility barriers never count as low performance."""
from __future__ import annotations

from django.db import transaction

from apps.analytics.models import StudentSkillStatus
from apps.analytics.services.aggregate import refresh_indicators_for_session
from apps.assessments.models import AssessmentResponse, AssessmentSession, ScoringRule, SessionSkillResult, SkillResultMapping
from apps.curriculum.models import StatusLabelConfig
from apps.interventions.services.recommend import recommend_template_for_result


@transaction.atomic
def score_session(session: AssessmentSession) -> SessionSkillResult | None:
    instrument = session.instrument
    skill = instrument.skill
    responses = list(session.responses.select_related("option", "item", "variant_used"))

    # Only responses that count toward learning (exclude N/A and accessibility blocks)
    scored_responses = [r for r in responses if r.counts_toward_score]
    raw_score = sum(r.score_value for r in scored_responses)

    # Max score only for items that were actually scorable in this session
    scorable_item_ids = {r.item_id for r in scored_responses}
    max_score = 0
    for item in instrument.items.prefetch_related("options"):
        if item.id not in scorable_item_ids:
            continue
        top = item.options.order_by("-score_value").values_list("score_value", flat=True).first() or 0
        max_score += top

    # Extra time / repeat instructions / large text must not reduce score
    # (already true — we ignore response_time and instruction_repeats here)

    used_equivalent = any(
        r.equivalence_applied == AssessmentResponse.EquivalenceApplied.EQUIVALENT for r in responses
    )
    used_alternative = any(
        r.equivalence_applied == AssessmentResponse.EquivalenceApplied.ALTERNATIVE for r in responses
    )
    a11y_note_parts = []
    if session.active_features:
        a11y_note_parts.append("recursos de acesso ativos")
    if used_equivalent:
        a11y_note_parts.append("variantes equivalentes")
    if used_alternative:
        a11y_note_parts.append("instrumento alternativo registrado")
    accessibility_note = "; ".join(a11y_note_parts)

    if not scored_responses:
        # No pedagogical performance data — do not invent low scores
        result, _ = SessionSkillResult.objects.update_or_create(
            session=session,
            skill=skill,
            defaults={
                "raw_score": 0,
                "max_score": 0,
                "result_code": "not_observed",
                "status_code": "not_observed",
                "status_label": _label_for(session.matrix_version_id, "not_observed"),
                "needs_attention": False,
                "recommended_template": None,
                "accessibility_note": accessibility_note or "sem itens aplicáveis por acessibilidade",
            },
        )
        return result

    rule = (
        ScoringRule.objects.filter(
            instrument=instrument, skill=skill, min_score__lte=raw_score, max_score__gte=raw_score
        )
        .order_by("min_score")
        .first()
    )

    if rule:
        result_code = rule.result_code
        status_code = rule.status_code
        status_label = rule.label or _label_for(session.matrix_version_id, status_code)
        mapping = SkillResultMapping.objects.filter(scoring_rule=rule).select_related("intervention_template").first()
        needs_attention = bool(mapping.needs_attention) if mapping else status_code in {
            "needs_support",
            "developing_with_support",
            "not_observed",
        }
        template = mapping.intervention_template if mapping else None
    else:
        ratio = (raw_score / max_score) if max_score else 0
        if ratio >= 0.9:
            status_code, result_code = "demonstrated", "demonstrated"
            needs_attention = False
        elif ratio >= 0.5:
            status_code, result_code = "developing", "developing"
            needs_attention = False
        else:
            status_code, result_code = "needs_support", "needs_support"
            needs_attention = True
        status_label = _label_for(session.matrix_version_id, status_code)
        template = None

    if template is None:
        template = recommend_template_for_result(skill=skill, status_code=status_code)

    result, _ = SessionSkillResult.objects.update_or_create(
        session=session,
        skill=skill,
        defaults={
            "raw_score": raw_score,
            "max_score": max_score,
            "result_code": result_code,
            "status_code": status_code,
            "status_label": status_label,
            "needs_attention": needs_attention,
            "recommended_template": template,
            "accessibility_note": accessibility_note,
        },
    )

    StudentSkillStatus.objects.update_or_create(
        student=session.enrollment.student,
        skill=skill,
        defaults={
            "enrollment": session.enrollment,
            "status_code": status_code,
            "status_label": status_label,
            "needs_attention": needs_attention,
            "last_session": session,
            "raw_score": raw_score,
            "max_score": max_score,
        },
    )

    refresh_indicators_for_session(session)
    return result


def _label_for(matrix_version_id: int, status_code: str) -> str:
    label = (
        StatusLabelConfig.objects.filter(matrix_version_id=matrix_version_id, code=status_code)
        .values_list("label", flat=True)
        .first()
    )
    defaults = {
        "not_observed": "Não observado",
        "needs_support": "Necessita maior mediação",
        "developing_with_support": "Desenvolvendo com apoio",
        "developing": "Em desenvolvimento",
        "demonstrated": "Habilidade demonstrada",
    }
    return label or defaults.get(status_code, status_code)
