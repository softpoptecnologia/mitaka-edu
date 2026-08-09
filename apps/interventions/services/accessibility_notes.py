"""Human-readable accessibility notes for groups and lesson plans."""
from __future__ import annotations

from apps.accessibility.models import AccessibilityFeature
from apps.assessments.services.resolver import AccessibilityAssessmentResolver
from apps.interventions.services.labels import first_name


def notes_for_students(*, records, instruments=None) -> tuple[list[str], list[str]]:
    """Return (notes, alternative_needed_names). Never treats access as low performance."""
    notes: list[str] = []
    needs_alternative: list[str] = []
    resolver = AccessibilityAssessmentResolver()
    instrument = (instruments or [None])[0] if instruments else None

    for record in records:
        codes = set(record.feature_codes or [])
        if not codes:
            continue
        name = first_name(record.student.full_name)
        blocked = False
        adapted = False
        if instrument is not None:
            resolved = resolver.resolve_instrument(student=record.student, instrument=instrument)
            if resolved.blocked_count:
                blocked = True
            if resolved.equivalent_count or resolved.alternative_count:
                adapted = True

        if AccessibilityFeature.Code.MOTOR_NO_DRAG in codes:
            if blocked and not adapted:
                needs_alternative.append(name)
                notes.append(f"Esta atividade precisa de uma alternativa para {name}.")
            else:
                notes.append(f"Esta atividade será apresentada sem arrastar para {name}.")
        if AccessibilityFeature.Code.VISUAL_SCREEN_READER in codes:
            if blocked and not adapted:
                needs_alternative.append(name)
                notes.append(f"Esta atividade precisa de uma alternativa para {name}.")
            else:
                notes.append(f"A atividade considera leitor de tela para {name}.")
        if AccessibilityFeature.Code.SENSORY_REDUCED_STIMULUS in codes:
            notes.append(f"Preparar a atividade com menos estímulos para {name}.")
        if AccessibilityFeature.Code.VISUAL_LARGE_TEXT in codes:
            notes.append(f"Usar texto ampliado para {name}.")
        if AccessibilityFeature.Code.COGNITIVE_STEP_BY_STEP in codes:
            notes.append(f"Oferecer instruções passo a passo para {name}.")
        if AccessibilityFeature.Code.AUDITORY_CAPTIONS in codes:
            notes.append(f"Incluir legendas ou apoio visual para {name}.")

    unique_notes = list(dict.fromkeys(notes))
    unique_alts = list(dict.fromkeys(needs_alternative))
    return unique_notes, unique_alts
