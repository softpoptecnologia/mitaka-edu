"""Teacher lesson planner views."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.selectors import user_can_access_classroom
from apps.core.permissions import TeacherRequiredMixin
from apps.interventions.services.settings import LESSON_DURATIONS
from apps.interventions.services.snapshot import load_classroom_snapshot
from apps.planning.services.lesson_builder import accept_lesson_proposal, build_lesson_proposal, normalize_duration
from apps.schools.models import Classroom


class LessonPlannerView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        if not user_can_access_classroom(request.user, classroom):
            messages.error(request, "Você não tem acesso a esta turma.")
            return redirect("teacher:home")
        duration = normalize_duration(request.GET.get("duracao") or 45)
        snapshot = load_classroom_snapshot(classroom)
        proposal = build_lesson_proposal(snapshot, duration_minutes=duration)
        return render(
            request,
            "teacher/lesson_plan.html",
            {
                "classroom": classroom,
                "proposal": proposal,
                "duration": duration,
                "durations": LESSON_DURATIONS,
            },
        )

    def post(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        if not user_can_access_classroom(request.user, classroom):
            messages.error(request, "Você não tem acesso a esta turma.")
            return redirect("teacher:home")
        duration = normalize_duration(request.POST.get("duracao") or request.POST.get("duration") or 45)
        snapshot = load_classroom_snapshot(classroom)
        proposal = build_lesson_proposal(snapshot, duration_minutes=duration)
        adjusted = request.POST.get("ajustar") == "1" or request.POST.get("action") == "adjust"
        # Allow simple minute overrides from the form without a giant admin form.
        for index, block in enumerate(proposal.blocks):
            raw = request.POST.get(f"minutes_{index}")
            if raw and str(raw).isdigit():
                block.minutes = max(1, min(int(raw), duration))
                adjusted = True
        plan = accept_lesson_proposal(
            user=request.user,
            snapshot=snapshot,
            proposal=proposal,
            adjusted=adjusted,
            apply_groups=request.POST.get("aplicar_grupos") != "0",
        )
        messages.success(request, "Plano da aula registrado.")
        return redirect("teacher:planning", pk=classroom.pk)
