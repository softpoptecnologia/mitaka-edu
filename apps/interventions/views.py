"""Intervention template catalog and status updates."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.accounts.selectors import user_can_access_student
from apps.core.permissions import ManagementRequiredMixin, TeacherRequiredMixin, cadastro_flags, can_write_network, user_role_code
from apps.core.services.cadastro import archive_object, audit, restore_object
from apps.interventions.forms import InterventionTemplateForm
from apps.interventions.models import InterventionStatus, InterventionTemplate, StudentIntervention


def _forbidden(request):
    return render(request, "admin_panel/forbidden.html", status=403)


def _can_write_template(user) -> bool:
    return can_write_network(user) or user_role_code(user) == "COORDENADOR"


class TemplateListView(ManagementRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "admin_panel/intervention_templates.html",
            {
                "templates": InterventionTemplate.objects.select_related("skill").order_by("skill__name", "title"),
                "can_write_template": _can_write_template(request.user),
                **cadastro_flags(request.user),
            },
        )


class TemplateCreateView(ManagementRequiredMixin, View):
    def get(self, request):
        if not _can_write_template(request.user):
            return _forbidden(request)
        return render(request, "admin_panel/form.html", {"form": InterventionTemplateForm(), "page_title": "Novo template de intervenção", "cancel_url": "management:intervention_templates"})

    def post(self, request):
        if not _can_write_template(request.user):
            return _forbidden(request)
        form = InterventionTemplateForm(request.POST)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": "Novo template de intervenção", "cancel_url": "management:intervention_templates"})
        obj = form.save()
        audit(request, "create", obj, f"Template criado: {obj.title}")
        messages.success(request, "Template cadastrado.")
        return redirect("management:intervention_templates")


class TemplateUpdateView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(InterventionTemplate, pk=pk)
        if not _can_write_template(request.user):
            return _forbidden(request)
        return render(request, "admin_panel/form.html", {"form": InterventionTemplateForm(instance=obj), "page_title": f"Editar template — {obj.title}", "cancel_url": "management:intervention_templates"})

    def post(self, request, pk):
        obj = get_object_or_404(InterventionTemplate, pk=pk)
        if not _can_write_template(request.user):
            return _forbidden(request)
        form = InterventionTemplateForm(request.POST, instance=obj)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": f"Editar template — {obj.title}", "cancel_url": "management:intervention_templates"})
        obj = form.save()
        audit(request, "update", obj, f"Template atualizado: {obj.title}")
        messages.success(request, "Template atualizado.")
        return redirect("management:intervention_templates")


class TemplateArchiveView(ManagementRequiredMixin, View):
    def post(self, request, pk):
        obj = get_object_or_404(InterventionTemplate, pk=pk)
        if not _can_write_template(request.user):
            return _forbidden(request)
        if obj.is_active:
            return archive_object(request, obj, redirect_to="management:intervention_templates")
        return restore_object(request, obj, redirect_to="management:intervention_templates")


class StudentInterventionStatusView(TeacherRequiredMixin, View):
    """Professor / gestão altera o ciclo da intervenção."""

    def post(self, request, pk):
        intervention = get_object_or_404(StudentIntervention, pk=pk)
        if not user_can_access_student(request.user, intervention.student):
            return _forbidden(request)
        status = request.POST.get("status")
        if status not in InterventionStatus.values:
            messages.error(request, "Situação inválida.")
            return redirect("teacher:student", pk=intervention.student_id)
        intervention.status = status
        intervention.save(update_fields=["status", "updated_at"])
        audit(request, "update", intervention, f"Intervenção {intervention.pk} → {status}")
        messages.success(request, "Situação da intervenção atualizada.")
        next_url = request.POST.get("next") or ""
        if next_url.startswith("/"):
            return redirect(next_url)
        return redirect(f"{reverse('teacher:student', args=[intervention.student_id])}?tab=intervencoes")
