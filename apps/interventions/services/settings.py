"""Centralized pedagogical parameters for teacher workflow.

Override via Django settings when needed. Do not scatter magic numbers.
"""
from __future__ import annotations

from django.conf import settings


def _get(name: str, default):
    return getattr(settings, name, default)


RECOMMENDED_GROUP_SIZE = _get("MITAKA_RECOMMENDED_GROUP_SIZE", 6)
MAX_GROUP_SIZE = _get("MITAKA_MAX_GROUP_SIZE", 8)
MIN_GROUP_SIZE = _get("MITAKA_MIN_GROUP_SIZE", 2)
MAX_SUGGESTED_GROUPS = _get("MITAKA_MAX_SUGGESTED_GROUPS", 3)
MAX_PRIORITY_SKILLS_PER_LESSON = _get("MITAKA_MAX_PRIORITY_SKILLS_PER_LESSON", 2)
MIN_ACTIVITY_MINUTES = _get("MITAKA_MIN_ACTIVITY_MINUTES", 10)
DEFAULT_ACTIVITY_MINUTES = _get("MITAKA_DEFAULT_ACTIVITY_MINUTES", 15)
WELCOME_MINUTES = _get("MITAKA_WELCOME_MINUTES", 5)
CLOSING_MINUTES = _get("MITAKA_CLOSING_MINUTES", 10)
DEFAULT_REASSESSMENT_DAYS = _get("MITAKA_DEFAULT_REASSESSMENT_DAYS", 7)
REASSESSMENT_DAYS_NEEDS_SUPPORT = _get("MITAKA_REASSESSMENT_DAYS_NEEDS_SUPPORT", 3)
FOLLOWUP_DUE_DAYS = _get("MITAKA_FOLLOWUP_DUE_DAYS", 1)
RECENT_FOLLOWUP_SUPPRESSION_DAYS = _get("MITAKA_RECENT_FOLLOWUP_SUPPRESSION_DAYS", 7)
TEMPLATE_REPEAT_AVOID_DAYS = _get("MITAKA_TEMPLATE_REPEAT_AVOID_DAYS", 14)
ACTION_DISMISS_HOURS = _get("MITAKA_ACTION_DISMISS_HOURS", 18)
LESSON_DURATIONS = _get("MITAKA_LESSON_DURATIONS", (30, 45, 60))

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

ACTION_ASSESSMENT_PENDING = "ASSESSMENT_PENDING"
ACTION_SKILL_GROUP_INTERVENTION = "SKILL_GROUP_INTERVENTION"
ACTION_INDIVIDUAL_INTERVENTION = "INDIVIDUAL_INTERVENTION"
ACTION_INTERVENTION_FOLLOWUP = "INTERVENTION_FOLLOWUP"
ACTION_REASSESSMENT_DUE = "REASSESSMENT_DUE"
ACTION_EVIDENCE_PENDING = "EVIDENCE_PENDING"
ACTION_ACCESSIBILITY_NOTICE = "ACCESSIBILITY_NOTICE"

PRIORITY_ORDER = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}

SKILL_DISPLAY_OVERRIDES = {
    "rimas": "Rimas",
    "segmentacao": "Segmentação silábica",
    "oralidade": "Reconto",
    "compreensao_oral": "Escuta compartilhada",
    "vocabulario": "Vocabulário",
    "consciencia_fonologica": "Consciência fonológica",
    "alfabetico": "Sistema alfabético",
}

FOLLOWUP_EVIDENCE_TEXTS = {
    "progressed": (
        "Participou da atividade {activity} em grupo. "
        "Apresentou avanço durante a atividade."
    ),
    "needs_more_support": (
        "Participou da atividade {activity} e ainda necessita de apoio "
        "na habilidade trabalhada."
    ),
    "not_observed": (
        "Não foi possível observar a participação na atividade {activity}."
    ),
}
