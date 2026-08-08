"""Cadastro de professores e vínculos com turmas."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.forms import TeacherClassroomForm, TeacherForm
from apps.accounts.models import Role, User
from apps.accounts.selectors import classrooms_for_user, schools_for_user
from apps.core.permissions import ManagementRequiredMixin, NETWORK_ROLES, can_hard_delete, can_write_school, user_role_code
from apps.core.services.cadastro import audit, hard_delete_object
from apps.schools.models import TeacherClassroom


def _forbidden(request):
    return render(request, "admin_panel/forbidden.html", status=403)


def _staff_qs(user):
    qs = User.objects.filter(userprofile__role__isnull=False).select_related(
        "userprofile", "userprofile__school", "userprofile__role"
    )
    code = user_role_code(user)
    if code not in NETWORK_ROLES:
        school_ids = schools_for_user(user, include_inactive=True).values_list("id", flat=True)
        qs = qs.filter(
            userprofile__school_id__in=school_ids,
            userprofile__role__code__in=[Role.Code.PROFESSOR, Role.Code.AEE, Role.Code.GESTOR, Role.Code.COORDENADOR],
        )
    elif code != Role.Code.SUPERADMIN:
        qs = qs.exclude(userprofile__role__code=Role.Code.SUPERADMIN)
    return qs.order_by("first_name", "username")


def _roles_for_user(user):
    qs = Role.objects.all().order_by("name")
    code = user_role_code(user)
    if code in NETWORK_ROLES:
        if code != Role.Code.SUPERADMIN:
            qs = qs.exclude(code=Role.Code.SUPERADMIN)
        return qs
    return qs.filter(code__in=[Role.Code.PROFESSOR, Role.Code.AEE])


_teachers_qs = _staff_qs


class TeacherCreateView(ManagementRequiredMixin, View):
    def get(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/form.html",
            {
                "form": TeacherForm(schools=schools_for_user(request.user), roles=_roles_for_user(request.user)),
                "page_title": "Novo usuário da equipe",
                "cancel_url": "management:teachers",
            },
        )

    def post(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        form = TeacherForm(request.POST, schools=schools_for_user(request.user), roles=_roles_for_user(request.user))
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": "Novo usuário da equipe", "cancel_url": "management:teachers"},
            )
        if not can_write_school(request.user, form.cleaned_data["school"]):
            return _forbidden(request)
        teacher = form.save()
        audit(request, "create", teacher, f"Usuário criado: {teacher.username}")
        messages.success(request, "Usuário cadastrado.")
        return redirect("management:teachers")


class TeacherUpdateView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        teacher = get_object_or_404(_teachers_qs(request.user), pk=pk)
        school = teacher.profile.school if teacher.profile else None
        if not can_write_school(request.user, school):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/form.html",
            {
                "form": TeacherForm(instance=teacher, schools=schools_for_user(request.user), roles=_roles_for_user(request.user)),
                "page_title": f"Editar usuário — {teacher.get_full_name() or teacher.username}",
                "cancel_url": "management:teachers",
            },
        )

    def post(self, request, pk):
        teacher = get_object_or_404(_teachers_qs(request.user), pk=pk)
        school = teacher.profile.school if teacher.profile else None
        if not can_write_school(request.user, school):
            return _forbidden(request)
        form = TeacherForm(request.POST, instance=teacher, schools=schools_for_user(request.user), roles=_roles_for_user(request.user))
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {
                    "form": form,
                    "page_title": f"Editar usuário — {teacher.get_full_name() or teacher.username}",
                    "cancel_url": "management:teachers",
                },
            )
        if not can_write_school(request.user, form.cleaned_data["school"]):
            return _forbidden(request)
        teacher = form.save()
        audit(request, "update", teacher, f"Usuário atualizado: {teacher.username}")
        messages.success(request, "Usuário atualizado.")
        return redirect("management:teachers")


class TeacherArchiveView(ManagementRequiredMixin, View):
    def post(self, request, pk):
        teacher = get_object_or_404(_teachers_qs(request.user), pk=pk)
        school = teacher.profile.school if teacher.profile else None
        if not can_write_school(request.user, school):
            return _forbidden(request)
        teacher.is_active = not teacher.is_active
        teacher.save(update_fields=["is_active"])
        audit(request, "update", teacher, f"Usuário {'reativado' if teacher.is_active else 'desativado'}: {teacher.username}")
        messages.success(request, "Usuário reativado." if teacher.is_active else "Usuário desativado.")
        return redirect("management:teachers")


class TeacherDeleteView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        teacher = get_object_or_404(_teachers_qs(request.user), pk=pk)
        if not can_hard_delete(request.user):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/confirm_delete.html",
            {
                "object": teacher,
                "object_label": teacher.get_full_name() or teacher.username,
                "cancel_url": "management:teachers",
                "warning": "Vínculos com turmas serão removidos. Prefira desativar o acesso.",
            },
        )

    def post(self, request, pk):
        teacher = get_object_or_404(_teachers_qs(request.user), pk=pk)
        school = teacher.profile.school if teacher.profile else None
        if not can_write_school(request.user, school):
            return _forbidden(request)
        return hard_delete_object(request, teacher, redirect_to="management:teachers")


class TeacherLinkCreateView(ManagementRequiredMixin, View):
    def get(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        form = TeacherClassroomForm(
            teachers=_staff_qs(request.user).filter(
                userprofile__role__code__in=[Role.Code.PROFESSOR, Role.Code.AEE]
            ),
            classrooms=classrooms_for_user(request.user),
        )
        return render(
            request,
            "admin_panel/form.html",
            {"form": form, "page_title": "Vincular professor à turma", "cancel_url": "management:teachers"},
        )

    def post(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        form = TeacherClassroomForm(
            request.POST,
            teachers=_staff_qs(request.user).filter(
                userprofile__role__code__in=[Role.Code.PROFESSOR, Role.Code.AEE]
            ),
            classrooms=classrooms_for_user(request.user),
        )
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": "Vincular professor à turma", "cancel_url": "management:teachers"},
            )
        classroom = form.cleaned_data["classroom"]
        if not can_write_school(request.user, classroom.school):
            return _forbidden(request)
        link = form.save()
        audit(request, "update", link, f"Vínculo professor-turma: {link}")
        messages.success(request, "Vínculo criado.")
        return redirect("management:teachers")


class TeacherLinkDeleteView(ManagementRequiredMixin, View):
    def post(self, request, pk):
        link = get_object_or_404(
            TeacherClassroom.objects.select_related("classroom", "classroom__school", "teacher"),
            pk=pk,
        )
        if not can_write_school(request.user, link.classroom.school):
            return _forbidden(request)
        if not classrooms_for_user(request.user, include_inactive=True).filter(pk=link.classroom_id).exists():
            return _forbidden(request)
        audit(request, "delete", link, f"Vínculo removido: {link}")
        link.delete()
        messages.success(request, "Vínculo removido.")
        return redirect("management:teachers")
