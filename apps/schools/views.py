"""Cadastro de escolas, turmas e anos letivos."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.selectors import classrooms_for_user, schools_for_user
from apps.core.permissions import (
    ManagementRequiredMixin,
    NetworkRequiredMixin,
    cadastro_flags,
    can_hard_delete,
    can_write_network,
    can_write_school,
)
from apps.core.services.cadastro import archive_object, audit, hard_delete_object, restore_object
from apps.schools.forms import ClassroomForm, MunicipalityForm, SchoolForm, SchoolYearForm
from apps.schools.models import Classroom, Municipality, School, SchoolYear
from apps.schools.services.school_year import activate_school_year


def _forbidden(request):
    return render(request, "admin_panel/forbidden.html", status=403)


class MunicipalityListView(NetworkRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "admin_panel/municipalities.html",
            {"municipalities": Municipality.objects.all(), **cadastro_flags(request.user)},
        )


class MunicipalityCreateView(NetworkRequiredMixin, View):
    def get(self, request):
        if not can_write_network(request.user):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/form.html",
            {"form": MunicipalityForm(), "page_title": "Novo município", "cancel_url": "management:municipalities"},
        )

    def post(self, request):
        if not can_write_network(request.user):
            return _forbidden(request)
        form = MunicipalityForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": "Novo município", "cancel_url": "management:municipalities"},
            )
        obj = form.save()
        audit(request, "create", obj, f"Município criado: {obj}")
        messages.success(request, "Município cadastrado.")
        return redirect("management:municipalities")


class MunicipalityUpdateView(NetworkRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(Municipality, pk=pk)
        return render(
            request,
            "admin_panel/form.html",
            {"form": MunicipalityForm(instance=obj), "page_title": f"Editar município — {obj.name}", "cancel_url": "management:municipalities"},
        )

    def post(self, request, pk):
        obj = get_object_or_404(Municipality, pk=pk)
        form = MunicipalityForm(request.POST, instance=obj)
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": f"Editar município — {obj.name}", "cancel_url": "management:municipalities"},
            )
        obj = form.save()
        audit(request, "update", obj, f"Município atualizado: {obj}")
        messages.success(request, "Município atualizado.")
        return redirect("management:municipalities")


class SchoolYearUpdateView(NetworkRequiredMixin, View):
    def get(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk)
        return render(
            request,
            "admin_panel/form.html",
            {"form": SchoolYearForm(instance=year), "page_title": f"Editar ano letivo — {year}", "cancel_url": "management:new_year"},
        )

    def post(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk)
        form = SchoolYearForm(request.POST, instance=year)
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": f"Editar ano letivo — {year}", "cancel_url": "management:new_year"},
            )
        year = form.save()
        audit(request, "update", year, f"Ano letivo atualizado: {year}")
        messages.success(request, "Ano letivo atualizado.")
        return redirect("management:new_year")


class SchoolCreateView(NetworkRequiredMixin, View):
    def get(self, request):
        if not can_write_network(request.user):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/form.html",
            {"form": SchoolForm(), "page_title": "Nova escola", "cancel_url": "management:schools"},
        )

    def post(self, request):
        if not can_write_network(request.user):
            return _forbidden(request)
        form = SchoolForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": "Nova escola", "cancel_url": "management:schools"},
            )
        school = form.save()
        audit(request, "create", school, f"Escola criada: {school.name}")
        messages.success(request, "Escola cadastrada.")
        return redirect("management:schools")


class SchoolUpdateView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        school = get_object_or_404(schools_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, school):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/form.html",
            {"form": SchoolForm(instance=school), "page_title": f"Editar escola — {school.name}", "cancel_url": "management:schools"},
        )

    def post(self, request, pk):
        school = get_object_or_404(schools_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, school):
            return _forbidden(request)
        form = SchoolForm(request.POST, instance=school)
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": f"Editar escola — {school.name}", "cancel_url": "management:schools"},
            )
        school = form.save()
        audit(request, "update", school, f"Escola atualizada: {school.name}")
        messages.success(request, "Escola atualizada.")
        return redirect("management:schools")


class SchoolArchiveView(ManagementRequiredMixin, View):
    def post(self, request, pk):
        school = get_object_or_404(schools_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_network(request.user):
            return _forbidden(request)
        if school.is_active:
            return archive_object(request, school, redirect_to="management:schools")
        return restore_object(request, school, redirect_to="management:schools")


class SchoolDeleteView(NetworkRequiredMixin, View):
    def get(self, request, pk):
        school = get_object_or_404(schools_for_user(request.user, include_inactive=True), pk=pk)
        if not can_hard_delete(request.user):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/confirm_delete.html",
            {
                "object": school,
                "object_label": school.name,
                "cancel_url": "management:schools",
                "warning": "Turmas e vínculos desta escola podem impedir a exclusão. Prefira desativar.",
            },
        )

    def post(self, request, pk):
        school = get_object_or_404(schools_for_user(request.user, include_inactive=True), pk=pk)
        blocked = school.classrooms.exists()
        return hard_delete_object(
            request,
            school,
            redirect_to="management:schools",
            blocked=blocked,
            block_message="A escola possui turmas. Desative-a em vez de excluir.",
        )


class ClassroomCreateView(ManagementRequiredMixin, View):
    def get(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        form = ClassroomForm(schools=schools_for_user(request.user))
        return render(
            request,
            "admin_panel/form.html",
            {"form": form, "page_title": "Nova turma", "cancel_url": "management:classrooms"},
        )

    def post(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        form = ClassroomForm(request.POST, schools=schools_for_user(request.user))
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": "Nova turma", "cancel_url": "management:classrooms"},
            )
        if not can_write_school(request.user, form.cleaned_data["school"]):
            return _forbidden(request)
        classroom = form.save()
        audit(request, "create", classroom, f"Turma criada: {classroom}")
        messages.success(request, "Turma cadastrada.")
        return redirect("management:classrooms")


class ClassroomUpdateView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        classroom = get_object_or_404(classrooms_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, classroom.school):
            return _forbidden(request)
        form = ClassroomForm(instance=classroom, schools=schools_for_user(request.user))
        return render(
            request,
            "admin_panel/form.html",
            {"form": form, "page_title": f"Editar turma — {classroom.name}", "cancel_url": "management:classrooms"},
        )

    def post(self, request, pk):
        classroom = get_object_or_404(classrooms_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, classroom.school):
            return _forbidden(request)
        form = ClassroomForm(request.POST, instance=classroom, schools=schools_for_user(request.user))
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": f"Editar turma — {classroom.name}", "cancel_url": "management:classrooms"},
            )
        if not can_write_school(request.user, form.cleaned_data["school"]):
            return _forbidden(request)
        classroom = form.save()
        audit(request, "update", classroom, f"Turma atualizada: {classroom}")
        messages.success(request, "Turma atualizada.")
        return redirect("management:classrooms")


class ClassroomArchiveView(ManagementRequiredMixin, View):
    def post(self, request, pk):
        classroom = get_object_or_404(classrooms_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, classroom.school):
            return _forbidden(request)
        if classroom.is_active:
            return archive_object(request, classroom, redirect_to="management:classrooms")
        return restore_object(request, classroom, redirect_to="management:classrooms")


class ClassroomDeleteView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        classroom = get_object_or_404(classrooms_for_user(request.user, include_inactive=True), pk=pk)
        if not can_hard_delete(request.user) or not can_write_school(request.user, classroom.school):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/confirm_delete.html",
            {
                "object": classroom,
                "object_label": f"{classroom.name} — {classroom.school.name}",
                "cancel_url": "management:classrooms",
                "warning": "Matrículas nesta turma impedem a exclusão. Prefira desativar.",
            },
        )

    def post(self, request, pk):
        classroom = get_object_or_404(classrooms_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, classroom.school):
            return _forbidden(request)
        return hard_delete_object(
            request,
            classroom,
            redirect_to="management:classrooms",
            blocked=classroom.enrollments.exists(),
            block_message="A turma possui matrículas. Desative-a em vez de excluir.",
        )


class SchoolYearActivateView(NetworkRequiredMixin, View):
    def post(self, request, pk):
        from apps.schools.models import SchoolYear

        year = get_object_or_404(SchoolYear, pk=pk)
        activate_school_year(year, actor=request.user)
        messages.success(request, f"Ano {year} ativado.")
        return redirect("management:new_year")
