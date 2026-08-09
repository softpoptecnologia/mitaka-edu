"""Registrar sondagem lúdica do app Flutter no domínio Django."""
from __future__ import annotations

from django.db import transaction

from apps.accounts.selectors import user_can_access_student
from apps.accounts.services.teacher_app import bootstrap_payload
from apps.analytics.models import StudentSkillStatus
from apps.assessments.models import AssessmentInstrument
from apps.assessments.services.session import complete_session, save_response, start_session
from apps.core.services.audit import log_action
from apps.curriculum.models import Skill
from apps.evidences.models import Evidence
from apps.students.models import Enrollment


class LudicActivityError(ValueError):
    pass


def _status_from_ratio(*, ratio: float, observational: bool, total_score: int) -> tuple[str, str, bool]:
    if observational:
        if total_score >= 3:
            return "demonstrated", "Habilidade demonstrada", False
        if total_score == 2:
            return "developing", "Desenvolvendo com apoio", False
        if total_score == 1:
            return "needs_support", "Necessita maior mediação", True
        return "not_observed", "Não observado", False
    if ratio >= 0.8:
        return "demonstrated", "Habilidade demonstrada", False
    if ratio >= 0.5:
        return "developing", "Em desenvolvimento", False
    return "needs_support", "Necessita maior mediação", True


@transaction.atomic
def record_ludic_activity(
    *,
    user,
    student_id: int,
    enrollment_id: int | None = None,
    activity_id: str,
    activity_title: str,
    skill_code: str,
    mode: str = "survey",
    label: str = "",
    score: int = 0,
    total: int = 0,
    needs_attention: bool | None = None,
    observation: str = "",
    answers: list | None = None,
    observational: bool = False,
) -> dict:
    from apps.students.models import Student

    try:
        student = Student.objects.get(pk=student_id, is_active=True)
    except Student.DoesNotExist as exc:
        raise LudicActivityError("Estudante não encontrado.") from exc
    if not user_can_access_student(user, student):
        raise LudicActivityError("Você não tem acesso a este estudante.")

    enrollment = None
    if enrollment_id:
        enrollment = Enrollment.objects.filter(pk=enrollment_id, student=student, is_active=True).select_related(
            "classroom", "school_year"
        ).first()
    if enrollment is None:
        enrollment = student.current_enrollment()
    if enrollment is None:
        raise LudicActivityError("Este estudante não tem matrícula ativa.")

    skill = (
        Skill.objects.filter(code=skill_code).first()
        or Skill.objects.filter(bncc_code=skill_code).first()
    )
    answers = answers or []
    total = total or len(answers) or 1
    ratio = (score / total) if total else 0
    status_code, status_label, inferred_attention = _status_from_ratio(
        ratio=ratio,
        observational=observational,
        total_score=score,
    )
    if needs_attention is None:
        needs_attention = inferred_attention
    if label:
        status_label = label

    description_parts = [
        f"Sondagem lúdica no app: {activity_title} ({activity_id}).",
        f"Modo: {'sondagem' if mode == 'survey' else 'praticar'}.",
        f"Resultado: {status_label} ({score}/{total}).",
    ]
    if observation.strip():
        description_parts.append(f"Observação: {observation.strip()}")
    description = " ".join(description_parts)

    evidence = Evidence.objects.create(
        enrollment=enrollment,
        student=student,
        skill=skill,
        recorded_by=user,
        description=description,
        file_type=Evidence.FileType.TEXT,
        visible_to_family=False,
    )

    session = None
    if mode == "survey" and skill:
        instrument = (
            AssessmentInstrument.objects.filter(skill=skill, is_published=True, is_active=True)
            .order_by("id")
            .first()
        )
        if instrument:
            session = start_session(enrollment=enrollment, instrument=instrument, started_by=user)
            items = list(instrument.items.order_by("order", "id").prefetch_related("options"))
            for index, item in enumerate(items):
                options = list(item.options.all())
                if not options:
                    continue
                correctish = False
                if index < len(answers):
                    answer = answers[index]
                    correctish = bool(answer.get("correct") or (answer.get("score") or 0) > 0)
                elif ratio >= 0.5:
                    correctish = True
                chosen = max(options, key=lambda o: o.score_value) if correctish else min(options, key=lambda o: o.score_value)
                save_response(
                    session=session,
                    item=item,
                    option=chosen,
                    text_value=observation.strip(),
                    applied_by=user,
                    is_observational=observational or instrument.instrument_type == AssessmentInstrument.InstrumentType.OBSERVATIONAL,
                )
            session = complete_session(session)
        else:
            StudentSkillStatus.objects.update_or_create(
                student=student,
                skill=skill,
                defaults={
                    "enrollment": enrollment,
                    "status_code": status_code,
                    "status_label": status_label,
                    "needs_attention": bool(needs_attention),
                    "raw_score": score,
                    "max_score": total,
                },
            )

    log_action(
        actor=user,
        action="create",
        object_type="LudicActivity",
        object_id=evidence.pk,
        message="Sondagem lúdica registrada pelo app do professor",
        payload={
            "student_id": student.pk,
            "activity_id": activity_id,
            "skill_code": skill_code,
            "mode": mode,
            "session_id": session.pk if session else None,
            "evidence_id": evidence.pk,
        },
    )
    return {
        "evidence_id": evidence.pk,
        "session_id": session.pk if session else None,
        "status_label": status_label,
        "needs_attention": bool(needs_attention),
        "bootstrap": bootstrap_payload(user),
    }
