"""Teacher operational views: groups, apply, quick follow-up."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.accounts.selectors import user_can_access_classroom, user_can_access_student
from apps.core.permissions import TeacherRequiredMixin
from apps.curriculum.models import Skill
from apps.interventions.models import ClassroomIntervention, FollowupResult, StudentIntervention
from apps.interventions.services.apply_group import apply_suggested_group
from apps.interventions.services.grouping import suggest_group_for_skill
from apps.interventions.services.labels import skill_label
from apps.interventions.services.quick_followup import (
    followup_targets_for_classroom_intervention,
    record_batch_followup,
)
from apps.interventions.services.snapshot import load_classroom_snapshot
from apps.interventions.services.teacher_actions import dismiss_action
from apps.schools.models import Classroom


class SuggestedGroupView(TeacherRequiredMixin, View):
    def get(self, request, classroom_id, skill_id):
        classroom = get_object_or_404(Classroom, pk=classroom_id)
        if not user_can_access_classroom(request.user, classroom):
            messages.error(request, "Você não tem acesso a esta turma.")
            return redirect("teacher:home")
        snapshot = load_classroom_snapshot(classroom)
        requested_ids = [int(x) for x in request.GET.getlist("estudante") if str(x).isdigit()]
        group = suggest_group_for_skill(snapshot, skill_id, student_ids=requested_ids or None)
        if group is None:
            skill = get_object_or_404(Skill.objects.select_related("dimension"), pk=skill_id)
            group = suggest_group_for_skill(
                snapshot,
                skill_id,
                student_ids=[r.student_id for r in snapshot.records],
            )
            if group is None:
                messages.info(request, "Não há sugestão de grupo para esta habilidade no momento.")
                return redirect("teacher:classroom", pk=classroom.pk)
            group.skill = group.skill or skill
        classmates = [r.student for r in snapshot.records]
        instruments = snapshot.instruments_by_skill_id.get(skill_id) or []
        instrument = instruments[0] if instruments else None
        play_rows = []
        if instrument and group:
            for enrollment in group.enrollments:
                play_rows.append(
                    {
                        "student": enrollment.student,
                        "preview_url": reverse("assessment:preview", args=[enrollment.pk, instrument.pk]),
                    }
                )
        return render(
            request,
            "teacher/suggested_group.html",
            {
                "classroom": classroom,
                "group": group,
                "classmates": classmates,
                "instrument": instrument,
                "play_rows": play_rows,
                "start_url": play_rows[0]["preview_url"] if play_rows else "",
                "why": request.GET.get("porque") == "1",
            },
        )

    def post(self, request, classroom_id, skill_id):
        classroom = get_object_or_404(Classroom, pk=classroom_id)
        if not user_can_access_classroom(request.user, classroom):
            messages.error(request, "Você não tem acesso a esta turma.")
            return redirect("teacher:home")
        if request.POST.get("ignorar"):
            dismiss_action(
                user=request.user,
                action_key=f"SKILL_GROUP_INTERVENTION:{classroom.pk}:{skill_id}:0",
                classroom_id=classroom.pk,
            )
            dismiss_action(
                user=request.user,
                action_key=f"INDIVIDUAL_INTERVENTION:{classroom.pk}:{skill_id}:0",
                classroom_id=classroom.pk,
            )
            messages.success(request, "Sugestão ignorada por enquanto.")
            return redirect("teacher:home")
        student_ids = [int(x) for x in request.POST.getlist("student_ids") if str(x).isdigit()]
        snapshot = load_classroom_snapshot(classroom)
        allowed = {r.student_id for r in snapshot.records}
        student_ids = [sid for sid in student_ids if sid in allowed]
        if not student_ids:
            messages.error(request, "Selecione pelo menos um estudante da turma.")
            return redirect("teacher:suggested_group", classroom_id=classroom.pk, skill_id=skill_id)
        group = suggest_group_for_skill(snapshot, skill_id, student_ids=student_ids)
        skill = get_object_or_404(Skill, pk=skill_id)
        result = apply_suggested_group(
            user=request.user,
            classroom=classroom,
            skill=skill,
            student_ids=student_ids,
            template=group.template if group else None,
        )
        if result.created:
            messages.success(request, "Intervenção registrada. Agora você pode acompanhar como foi a atividade.")
        else:
            messages.info(request, "Esta intervenção já estava registrada. Você pode acompanhar o grupo.")
        return redirect("teacher:quick_followup", pk=result.classroom_intervention.pk)


class PendingAssessmentsView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        if not user_can_access_classroom(request.user, classroom):
            messages.error(request, "Você não tem acesso a esta turma.")
            return redirect("teacher:home")
        snapshot = load_classroom_snapshot(classroom)
        rows = []
        for record in snapshot.records:
            if record.has_completed_session:
                continue
            instrument = None
            for skill_id, instruments in snapshot.instruments_by_skill_id.items():
                if instruments and skill_id not in record.completed_skill_ids:
                    instrument = instruments[0]
                    break
            if instrument is None:
                continue
            rows.append(
                {
                    "student": record.student,
                    "enrollment": record.enrollment,
                    "instrument": instrument,
                    "skill_name": skill_label(instrument.skill),
                    "preview_url": reverse("assessment:preview", args=[record.enrollment.pk, instrument.pk]),
                }
            )
        return render(
            request,
            "teacher/pending_assessments.html",
            {"classroom": classroom, "rows": rows},
        )


class QuickFollowupView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        intervention = get_object_or_404(
            ClassroomIntervention.objects.select_related("classroom", "skill", "skill__dimension", "template"),
            pk=pk,
        )
        if not user_can_access_classroom(request.user, intervention.classroom):
            messages.error(request, "Você não tem acesso a esta atividade.")
            return redirect("teacher:home")
        targets = followup_targets_for_classroom_intervention(intervention)
        if not targets:
            snapshot = load_classroom_snapshot(intervention.classroom)
            group = suggest_group_for_skill(snapshot, intervention.skill_id)
            student_ids = group.student_ids if group else [r.student_id for r in snapshot.records]
            if student_ids:
                apply_suggested_group(
                    user=request.user,
                    classroom=intervention.classroom,
                    skill=intervention.skill,
                    student_ids=student_ids,
                    template=intervention.template,
                )
                targets = followup_targets_for_classroom_intervention(intervention)
        return render(
            request,
            "teacher/quick_followup.html",
            {
                "classroom": intervention.classroom,
                "intervention": intervention,
                "targets": targets,
                "results": FollowupResult,
                "activity_title": intervention.template.title if intervention.template_id else intervention.skill.name,
            },
        )

    def post(self, request, pk):
        intervention = get_object_or_404(
            ClassroomIntervention.objects.select_related("classroom", "skill", "template"),
            pk=pk,
        )
        if not user_can_access_classroom(request.user, intervention.classroom):
            messages.error(request, "Você não tem acesso a esta atividade.")
            return redirect("teacher:home")
        targets = followup_targets_for_classroom_intervention(intervention)
        results = {}
        for target in targets:
            value = request.POST.get(f"result_{target.pk}") or request.POST.get(f"result_{target.student_id}")
            if value:
                results[target.pk] = value
        if not results:
            messages.error(request, "Registre o resultado de pelo menos um estudante.")
            return redirect("teacher:quick_followup", pk=intervention.pk)
        record_batch_followup(
            user=request.user,
            interventions=targets,
            results=results,
            general_notes=(request.POST.get("general_notes") or "").strip(),
            classroom_intervention=intervention,
        )
        messages.success(request, "Acompanhamentos salvos.")
        return redirect("teacher:home")


class StudentQuickFollowupView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        intervention = get_object_or_404(
            StudentIntervention.objects.select_related("student", "enrollment", "skill", "skill__dimension", "template", "enrollment__classroom"),
            pk=pk,
        )
        if not user_can_access_student(request.user, intervention.student):
            messages.error(request, "Você não tem acesso a este estudante.")
            return redirect("teacher:home")
        return render(
            request,
            "teacher/quick_followup.html",
            {
                "classroom": intervention.enrollment.classroom if intervention.enrollment_id else None,
                "intervention": None,
                "student_intervention": intervention,
                "targets": [intervention],
                "results": FollowupResult,
                "activity_title": intervention.template.title if intervention.template_id else intervention.skill.name,
            },
        )

    def post(self, request, pk):
        intervention = get_object_or_404(
            StudentIntervention.objects.select_related("student", "enrollment", "skill", "template"),
            pk=pk,
        )
        if not user_can_access_student(request.user, intervention.student):
            messages.error(request, "Você não tem acesso a este estudante.")
            return redirect("teacher:home")
        value = request.POST.get(f"result_{intervention.pk}") or request.POST.get(f"result_{intervention.student_id}")
        if not value:
            messages.error(request, "Selecione como foi a participação.")
            return redirect("teacher:quick_followup_student", pk=intervention.pk)
        record_batch_followup(
            user=request.user,
            interventions=[intervention],
            results={intervention.pk: value},
            general_notes=(request.POST.get("general_notes") or "").strip(),
            classroom_intervention=intervention.classroom_intervention,
        )
        messages.success(request, "Acompanhamento salvo.")
        return redirect("teacher:home")


class DismissActionView(TeacherRequiredMixin, View):
    def post(self, request):
        key = (request.POST.get("key") or "").strip()
        classroom_id = request.POST.get("classroom_id")
        if key:
            dismiss_action(user=request.user, action_key=key, classroom_id=int(classroom_id) if str(classroom_id).isdigit() else None)
            messages.success(request, "Sugestão ocultada por agora.")
        next_url = request.POST.get("next") or reverse("teacher:home")
        if next_url.startswith("/"):
            return redirect(next_url)
        return redirect("teacher:home")
