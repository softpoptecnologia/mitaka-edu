"""Curriculum authoring for técnico / secretaria."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.core.permissions import NetworkRequiredMixin, can_write_network
from apps.core.services.cadastro import audit
from apps.curriculum.forms import DimensionForm, MatrixForm, MatrixVersionForm, SkillForm, ensure_default_status_labels
from apps.curriculum.models import DevelopmentDimension, MatrixVersion, PedagogicalMatrix, Skill


def _forbidden(request):
    return render(request, "admin_panel/forbidden.html", status=403)


class MatrixCreateView(NetworkRequiredMixin, View):
    def get(self, request):
        if not can_write_network(request.user):
            return _forbidden(request)
        return render(request, "admin_panel/form.html", {"form": MatrixForm(), "page_title": "Nova matriz", "cancel_url": "management:matrix"})

    def post(self, request):
        if not can_write_network(request.user):
            return _forbidden(request)
        form = MatrixForm(request.POST)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": "Nova matriz", "cancel_url": "management:matrix"})
        matrix = form.save()
        audit(request, "create", matrix, f"Matriz criada: {matrix.name}")
        messages.success(request, "Matriz cadastrada.")
        return redirect("management:matrix")


class MatrixUpdateView(NetworkRequiredMixin, View):
    def get(self, request, pk):
        matrix = get_object_or_404(PedagogicalMatrix, pk=pk)
        return render(request, "admin_panel/form.html", {"form": MatrixForm(instance=matrix), "page_title": f"Editar matriz — {matrix.name}", "cancel_url": "management:matrix"})

    def post(self, request, pk):
        matrix = get_object_or_404(PedagogicalMatrix, pk=pk)
        form = MatrixForm(request.POST, instance=matrix)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": f"Editar matriz — {matrix.name}", "cancel_url": "management:matrix"})
        matrix = form.save()
        audit(request, "update", matrix, f"Matriz atualizada: {matrix.name}")
        messages.success(request, "Matriz atualizada.")
        return redirect("management:matrix")


class MatrixVersionCreateView(NetworkRequiredMixin, View):
    def get(self, request):
        form = MatrixVersionForm(initial={"matrix": request.GET.get("matriz")})
        return render(request, "admin_panel/form.html", {"form": form, "page_title": "Nova versão da matriz", "cancel_url": "management:matrix"})

    def post(self, request):
        form = MatrixVersionForm(request.POST)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": "Nova versão da matriz", "cancel_url": "management:matrix"})
        version = form.save()
        ensure_default_status_labels(version)
        audit(request, "create", version, f"Versão criada: {version}")
        messages.success(request, "Versão criada com nomenclatura pedagógica padrão.")
        return redirect("management:matrix")


class MatrixVersionPublishView(NetworkRequiredMixin, View):
    def post(self, request, pk):
        version = get_object_or_404(MatrixVersion, pk=pk)
        version.is_published = not version.is_published
        version.published_at = timezone.now() if version.is_published else None
        version.save(update_fields=["is_published", "published_at", "updated_at"])
        if version.is_published:
            MatrixVersion.objects.filter(matrix=version.matrix).exclude(pk=version.pk).update(is_published=False)
            ensure_default_status_labels(version)
        audit(request, "update", version, f"Versão {'publicada' if version.is_published else 'despublicada'}: {version}")
        messages.success(request, "Versão publicada." if version.is_published else "Versão despublicada.")
        return redirect("management:matrix")


class DimensionCreateView(NetworkRequiredMixin, View):
    def get(self, request):
        form = DimensionForm(initial={"matrix_version": request.GET.get("versao")})
        return render(request, "admin_panel/form.html", {"form": form, "page_title": "Nova dimensão", "cancel_url": "management:dimensions"})

    def post(self, request):
        form = DimensionForm(request.POST)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": "Nova dimensão", "cancel_url": "management:dimensions"})
        obj = form.save()
        audit(request, "create", obj, f"Dimensão criada: {obj.name}")
        messages.success(request, "Dimensão cadastrada.")
        return redirect("management:dimensions")


class DimensionUpdateView(NetworkRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(DevelopmentDimension, pk=pk)
        return render(request, "admin_panel/form.html", {"form": DimensionForm(instance=obj), "page_title": f"Editar dimensão — {obj.name}", "cancel_url": "management:dimensions"})

    def post(self, request, pk):
        obj = get_object_or_404(DevelopmentDimension, pk=pk)
        form = DimensionForm(request.POST, instance=obj)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": f"Editar dimensão — {obj.name}", "cancel_url": "management:dimensions"})
        obj = form.save()
        audit(request, "update", obj, f"Dimensão atualizada: {obj.name}")
        messages.success(request, "Dimensão atualizada.")
        return redirect("management:dimensions")


class SkillCreateView(NetworkRequiredMixin, View):
    def get(self, request):
        form = SkillForm(initial={"dimension": request.GET.get("dimensao")})
        return render(request, "admin_panel/form.html", {"form": form, "page_title": "Nova habilidade", "cancel_url": "management:dimensions"})

    def post(self, request):
        form = SkillForm(request.POST)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": "Nova habilidade", "cancel_url": "management:dimensions"})
        obj = form.save()
        audit(request, "create", obj, f"Habilidade criada: {obj.name}")
        messages.success(request, "Habilidade cadastrada.")
        return redirect("management:dimensions")


class SkillUpdateView(NetworkRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(Skill, pk=pk)
        return render(request, "admin_panel/form.html", {"form": SkillForm(instance=obj), "page_title": f"Editar habilidade — {obj.name}", "cancel_url": "management:dimensions"})

    def post(self, request, pk):
        obj = get_object_or_404(Skill, pk=pk)
        form = SkillForm(request.POST, instance=obj)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": f"Editar habilidade — {obj.name}", "cancel_url": "management:dimensions"})
        obj = form.save()
        audit(request, "update", obj, f"Habilidade atualizada: {obj.name}")
        messages.success(request, "Habilidade atualizada.")
        return redirect("management:dimensions")
