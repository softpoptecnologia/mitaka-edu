"""Seedable catalog of functional accessibility features."""
from __future__ import annotations

from apps.accessibility.models import AccessibilityCategory, AccessibilityFeature

FEATURE_SPECS = [
    (AccessibilityCategory.Code.VISUAL, AccessibilityFeature.Code.VISUAL_SCREEN_READER, "Leitor de tela", "a11y-screen-reader", 10),
    (AccessibilityCategory.Code.VISUAL, AccessibilityFeature.Code.VISUAL_HIGH_CONTRAST, "Alto contraste", "a11y-high-contrast", 20),
    (AccessibilityCategory.Code.VISUAL, AccessibilityFeature.Code.VISUAL_LARGE_TEXT, "Texto ampliado", "a11y-large-text", 30),
    (AccessibilityCategory.Code.AUDITORY, AccessibilityFeature.Code.AUDITORY_CAPTIONS, "Legendas", "", 10),
    (AccessibilityCategory.Code.AUDITORY, AccessibilityFeature.Code.AUDITORY_VISUAL_INSTRUCTION, "Instrução visual", "", 20),
    (AccessibilityCategory.Code.AUDITORY, AccessibilityFeature.Code.AUDITORY_LIBRAS, "Libras", "", 30),
    (AccessibilityCategory.Code.MOTOR, AccessibilityFeature.Code.MOTOR_LARGE_TARGET, "Alvos ampliados", "a11y-large-target", 10),
    (AccessibilityCategory.Code.MOTOR, AccessibilityFeature.Code.MOTOR_KEYBOARD, "Navegação por teclado", "", 20),
    (AccessibilityCategory.Code.MOTOR, AccessibilityFeature.Code.MOTOR_NO_DRAG, "Sem arrastar e soltar", "", 30),
    (AccessibilityCategory.Code.COGNITIVE, AccessibilityFeature.Code.COGNITIVE_SHORT_INSTRUCTIONS, "Instruções curtas", "", 10),
    (AccessibilityCategory.Code.COGNITIVE, AccessibilityFeature.Code.COGNITIVE_EXTRA_TIME, "Tempo ampliado", "", 20),
    (AccessibilityCategory.Code.COGNITIVE, AccessibilityFeature.Code.COGNITIVE_STEP_BY_STEP, "Instruções passo a passo", "a11y-step-by-step", 30),
    (AccessibilityCategory.Code.COGNITIVE, AccessibilityFeature.Code.COGNITIVE_NO_TIME_LIMIT, "Sem limite rígido de tempo", "", 40),
    (AccessibilityCategory.Code.COGNITIVE, AccessibilityFeature.Code.COGNITIVE_REPEAT_INSTRUCTIONS, "Repetição de instruções", "", 50),
    (AccessibilityCategory.Code.SENSORY, AccessibilityFeature.Code.SENSORY_REDUCED_MOTION, "Redução de animações", "a11y-reduced-motion", 10),
    (AccessibilityCategory.Code.SENSORY, AccessibilityFeature.Code.SENSORY_REDUCED_STIMULUS, "Redução de estímulos", "a11y-reduced-stimulus", 20),
]

CATEGORY_ORDER = {
    AccessibilityCategory.Code.VISUAL: 10,
    AccessibilityCategory.Code.AUDITORY: 20,
    AccessibilityCategory.Code.MOTOR: 30,
    AccessibilityCategory.Code.COGNITIVE: 40,
    AccessibilityCategory.Code.SENSORY: 50,
    AccessibilityCategory.Code.COMMUNICATION: 60,
}


def ensure_default_features() -> dict[str, AccessibilityFeature]:
    features: dict[str, AccessibilityFeature] = {}
    categories: dict[str, AccessibilityCategory] = {}
    for code, label in AccessibilityCategory.Code.choices:
        cat, _ = AccessibilityCategory.objects.update_or_create(
            code=code,
            defaults={"name": label, "order": CATEGORY_ORDER.get(code, 99)},
        )
        categories[code] = cat
    for cat_code, feat_code, name, css_class, order in FEATURE_SPECS:
        feat, _ = AccessibilityFeature.objects.update_or_create(
            code=feat_code,
            defaults={
                "category": categories[cat_code],
                "name": name,
                "css_class": css_class,
                "order": order,
                "is_active": True,
            },
        )
        features[feat_code] = feat
    return features
