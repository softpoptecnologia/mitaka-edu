"""Assessment player views — accessible adaptive experience."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.http import require_POST

from apps.accounts.selectors import user_can_access_enrollment
from apps.accessibility.permissions import active_resource_labels_for_teacher
from apps.assessments.models import (
    AssessmentInstrument,
    AssessmentOption,
    AssessmentResponse,
    AssessmentSession,
)
from apps.assessments.services import (
    AccessibilityAssessmentResolver,
    complete_session,
    preview_adapted_assessment,
    save_response,
    start_session,
)
from apps.assessments.services.resolver import css_classes_for_features
from apps.core.permissions import TeacherRequiredMixin
from apps.students.models import Enrollment


def _can_access_session(user, session: AssessmentSession) -> bool:
    return user_can_access_enrollment(user, session.enrollment)


class PreviewAdaptedAssessmentView(TeacherRequiredMixin, View):
    """Teacher sees automatic adaptation before starting."""

    def get(self, request, enrollment_id, instrument_id):
        enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
        if not user_can_access_enrollment(request.user, enrollment):
            messages.error(request, "Acesso negado.")
            return redirect("teacher:home")
        instrument = get_object_or_404(
            AssessmentInstrument, pk=instrument_id, is_published=True, is_active=True
        )
        preview = preview_adapted_assessment(student=enrollment.student, instrument=instrument)
        return render(
            request,
            "assessment/preview_adapted.html",
            {
                "enrollment": enrollment,
                "student": enrollment.student,
                "instrument": instrument,
                "plan": preview["plan"],
                "summary": preview["summary"],
                "feature_names": preview["feature_names"],
                "resource_labels": active_resource_labels_for_teacher(enrollment.student),
            },
        )


class PrintAccessibleAssessmentView(TeacherRequiredMixin, View):
    def get(self, request, enrollment_id, instrument_id):
        enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
        if not user_can_access_enrollment(request.user, enrollment):
            messages.error(request, "Acesso negado.")
            return redirect("teacher:home")
        instrument = get_object_or_404(AssessmentInstrument, pk=instrument_id, is_active=True)
        preview = preview_adapted_assessment(student=enrollment.student, instrument=instrument)
        return render(
            request,
            "assessment/print_accessible.html",
            {
                "enrollment": enrollment,
                "student": enrollment.student,
                "instrument": instrument,
                "plan": preview["plan"],
                "feature_names": preview["feature_names"],
            },
        )


class StartAssessmentView(TeacherRequiredMixin, View):
    def post(self, request, enrollment_id, instrument_id):
        enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
        if not user_can_access_enrollment(request.user, enrollment):
            messages.error(request, "Acesso negado.")
            return redirect("teacher:home")
        instrument = get_object_or_404(
            AssessmentInstrument, pk=instrument_id, is_published=True, is_active=True
        )
        observational = request.POST.get("observational") == "1"
        if observational:
            instrument_obs = instrument
            # Force observational application mode via session fields after start
            session = start_session(enrollment=enrollment, instrument=instrument_obs, started_by=request.user)
            session.application_mode = AssessmentSession.ApplicationMode.OBSERVATIONAL
            session.save(update_fields=["application_mode", "updated_at"])
        else:
            session = start_session(enrollment=enrollment, instrument=instrument, started_by=request.user)
        return redirect("assessment:play", session_id=session.pk)


class PlayAssessmentView(TeacherRequiredMixin, View):
    def get(self, request, session_id):
        session = get_object_or_404(AssessmentSession, pk=session_id)
        if not _can_access_session(request.user, session):
            messages.error(request, "Acesso negado.")
            return redirect("teacher:home")
        if session.status == AssessmentSession.Status.COMPLETED:
            return redirect("teacher:session_result", pk=session.pk)
        if session.status in {
            AssessmentSession.Status.REQUIRES_ALTERNATIVE_INSTRUMENT,
            AssessmentSession.Status.ACCESSIBILITY_BLOCKED,
            AssessmentSession.Status.NOT_APPLICABLE,
            AssessmentSession.Status.PARTIALLY_COMPLETED,
        }:
            return redirect("teacher:session_result", pk=session.pk)

        items = list(session.instrument.items.prefetch_related("options").order_by("order", "id"))
        answered_ids = set(session.responses.values_list("item_id", flat=True))
        current = next((item for item in items if item.id not in answered_ids), None)
        if current is None:
            complete_session(session)
            return redirect("teacher:session_result", pk=session.pk)

        resolved = AccessibilityAssessmentResolver().resolve_item(
            student=session.enrollment.student, assessment_item=current
        )

        # Auto-register blocked items without counting as error
        if resolved.equivalence in {
            AssessmentResponse.EquivalenceApplied.REQUIRES_ALTERNATIVE,
            AssessmentResponse.EquivalenceApplied.BLOCKED,
            AssessmentResponse.EquivalenceApplied.NOT_APPLICABLE,
        }:
            save_response(
                session=session,
                item=current,
                applied_by=request.user,
                text_value=resolved.reason,
            )
            return redirect("assessment:play", session_id=session.pk)

        progress = int(100 * len(answered_ids) / max(len(items), 1))
        a11y_classes = css_classes_for_features(session.active_features or resolved.active_features)
        options = list(current.options.all())
        short_instructions = "COGNITIVE_SHORT_INSTRUCTIONS" in (session.active_features or [])
        step_by_step = "COGNITIVE_STEP_BY_STEP" in (session.active_features or [])
        prompt = resolved.display_prompt
        if short_instructions and len(prompt) > 160:
            prompt = prompt[:157].rsplit(" ", 1)[0] + "…"

        return render(
            request,
            "assessment/play.html",
            {
                "session": session,
                "item": current,
                "resolved": resolved,
                "prompt": prompt,
                "prompt_image": resolved.prompt_image,
                "prompt_image_alt": resolved.prompt_image_alt,
                "prompt_audio": resolved.prompt_audio,
                "options": options,
                "progress": progress,
                "student": session.enrollment.student,
                "total": len(items),
                "answered": len(answered_ids),
                "is_observational": (
                    session.application_mode == AssessmentSession.ApplicationMode.OBSERVATIONAL
                    or session.instrument.instrument_type
                    == AssessmentInstrument.InstrumentType.OBSERVATIONAL
                ),
                "a11y_classes": " ".join(a11y_classes),
                "active_features": session.active_features,
                "equivalence": resolved.equivalence,
                "variant": resolved.variant,
                "step_by_step": step_by_step,
                "allow_repeat": "COGNITIVE_REPEAT_INSTRUCTIONS" in (session.active_features or []),
            },
        )


@login_required
@require_POST
def answer_item(request, session_id):
    session = get_object_or_404(AssessmentSession, pk=session_id)
    if not _can_access_session(request.user, session):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    item_id = request.POST.get("item_id")
    option_id = request.POST.get("option_id")
    item = get_object_or_404(session.instrument.items, pk=item_id)
    option = get_object_or_404(AssessmentOption, pk=option_id, item=item) if option_id else None
    repeats = int(request.POST.get("instruction_repeats") or 0)
    save_response(
        session=session,
        item=item,
        option=option,
        text_value=request.POST.get("text_value", ""),
        applied_by=request.user,
        instruction_repeats=repeats,
        is_observational=session.application_mode == AssessmentSession.ApplicationMode.OBSERVATIONAL,
    )
    wants_json = bool(request.headers.get("HX-Request")) or request.POST.get("format") == "json"
    if wants_json:
        return JsonResponse({"ok": True, "next": f"/avaliacao/sessao/{session.pk}/"})
    return redirect("assessment:play", session_id=session.pk)


@login_required
@require_POST
def finish_session(request, session_id):
    session = get_object_or_404(AssessmentSession, pk=session_id)
    if not _can_access_session(request.user, session):
        messages.error(request, "Acesso negado.")
        return redirect("teacher:home")
    complete_session(session)
    return redirect("teacher:session_result", pk=session.pk)
