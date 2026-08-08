"""AI service stubs — prepared for future local/private integrations.

MVP does NOT call external APIs and does not send child data outside the platform.
Recommendations are rule-based via interventions.services.recommend.
"""
from __future__ import annotations

from apps.interventions.services.recommend import recommend_template_for_result


def generate_plan(classroom, skill=None, **kwargs):
    """Future: assist pedagogical planning. MVP returns structured placeholder."""
    return {
        "status": "not_implemented_ai",
        "message": "Planejamento assistido por regras locais. IA futura opcional.",
        "classroom_id": classroom.pk if classroom else None,
        "skill_id": skill.pk if skill else None,
    }


def generate_student_summary(student, **kwargs):
    return {
        "status": "not_implemented_ai",
        "message": "Resumo disponível via relatórios HTML baseados em dados locais.",
        "student_id": student.pk if student else None,
    }


def suggest_intervention(skill, status_code: str, **kwargs):
    template = recommend_template_for_result(skill=skill, status_code=status_code)
    return {
        "source": "rules",
        "template_id": template.pk if template else None,
        "template": template,
    }


def analyze_classroom(classroom, **kwargs):
    return {
        "status": "not_implemented_ai",
        "message": "Análise de turma disponível nos dashboards e planejamento assistido.",
        "classroom_id": classroom.pk if classroom else None,
    }
