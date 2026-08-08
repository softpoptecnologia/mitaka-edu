"""AEE support plan write path."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.accessibility.forms import SupportPlanForm, SupportStrategyForm
from apps.accessibility.models import StudentSupportPlan
from apps.accessibility.permissions import can_manage_support_plan
from apps.accessibility.services.catalog import ensure_default_features
from apps.core.permissions import AEERequiredMixin
from apps.core.services.cadastro import audit
from apps.schools.models import SchoolYear
from apps.students.models import Student


def _forbidden(request):
    return render(request, "admin_panel/forbidden.html", status=403)


class SupportPlanCreateView(AEERequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        if not can_manage_support_plan(request.user, student):
            return _forbidden(request)
        ensure_default_features()
        year = SchoolYear.objects.filter(is_active=True).first()
        return render(
            request,
            "teacher/support_plan_form.html",
            {"form": SupportPlanForm(initial={"school_year": year, "start_date": timezone.localdate()}), "student": student},
        )

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        if not can_manage_support_plan(request.user, student):
            return _forbidden(request)
        form = SupportPlanForm(request.POST)
        if not form.is_valid():
            return render(request, "teacher/support_plan_form.html", {"form": form, "student": student})
        plan = form.save(commit=False)
        plan.student = student
        plan.created_by = request.user
        plan.save()
        plan.responsible_users.add(request.user)
        audit(request, "support_plan", plan, f"Plano de apoio criado para {student}")
        messages.success(request, "Plano de apoio criado.")
        return redirect(f"{reverse('teacher:student', args=[student.pk])}?tab=apoio")


class SupportPlanUpdateView(AEERequiredMixin, View):
    def get(self, request, pk):
        plan = get_object_or_404(StudentSupportPlan, pk=pk)
        if not can_manage_support_plan(request.user, plan.student):
            return _forbidden(request)
        return render(
            request,
            "teacher/support_plan_form.html",
            {"form": SupportPlanForm(instance=plan), "student": plan.student, "plan": plan},
        )

    def post(self, request, pk):
        plan = get_object_or_404(StudentSupportPlan, pk=pk)
        if not can_manage_support_plan(request.user, plan.student):
            return _forbidden(request)
        form = SupportPlanForm(request.POST, instance=plan)
        if not form.is_valid():
            return render(request, "teacher/support_plan_form.html", {"form": form, "student": plan.student, "plan": plan})
        plan = form.save()
        audit(request, "support_plan", plan, f"Plano de apoio atualizado: {plan.student}")
        messages.success(request, "Plano de apoio atualizado.")
        return redirect(f"{reverse('teacher:student', args=[plan.student_id])}?tab=apoio")


class SupportStrategyCreateView(AEERequiredMixin, View):
    def get(self, request, pk):
        plan = get_object_or_404(StudentSupportPlan, pk=pk)
        if not can_manage_support_plan(request.user, plan.student):
            return _forbidden(request)
        ensure_default_features()
        return render(
            request,
            "teacher/support_strategy_form.html",
            {"form": SupportStrategyForm(), "student": plan.student, "plan": plan},
        )

    def post(self, request, pk):
        plan = get_object_or_404(StudentSupportPlan, pk=pk)
        if not can_manage_support_plan(request.user, plan.student):
            return _forbidden(request)
        form = SupportStrategyForm(request.POST)
        if not form.is_valid():
            return render(request, "teacher/support_strategy_form.html", {"form": form, "student": plan.student, "plan": plan})
        strategy = form.save(commit=False)
        strategy.support_plan = plan
        strategy.save()
        audit(request, "support_plan", strategy, f"Estratégia adicionada ao plano {plan.pk}")
        messages.success(request, "Estratégia adicionada.")
        return redirect(f"{reverse('teacher:student', args=[plan.student_id])}?tab=apoio")
