"""Cadastro de estudantes e matrículas."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.selectors import classrooms_for_user, enrollments_for_user, students_for_user
from apps.core.permissions import ManagementRequiredMixin, can_hard_delete, can_write_school
from apps.core.services.cadastro import archive_object, audit, hard_delete_object, restore_object
from apps.students.forms import EnrollmentForm, StudentForm
from apps.students.models import Enrollment, Student


def _forbidden(request):
    return render(request, "admin_panel/forbidden.html", status=403)


class StudentCreateView(ManagementRequiredMixin, View):
    def get(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        form = StudentForm(classrooms=classrooms_for_user(request.user))
        return render(
            request,
            "admin_panel/form.html",
            {"form": form, "page_title": "Novo estudante", "cancel_url": "management:students"},
        )

    def post(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        form = StudentForm(request.POST, classrooms=classrooms_for_user(request.user))
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": "Novo estudante", "cancel_url": "management:students"},
            )
        classroom = form.cleaned_data.get("classroom")
        if classroom and not can_write_school(request.user, classroom.school):
            return _forbidden(request)
        student = form.save()
        if classroom:
            Enrollment.objects.update_or_create(
                student=student,
                school_year=classroom.school_year,
                defaults={"classroom": classroom, "status": Enrollment.Status.ACTIVE, "is_active": True},
            )
        audit(request, "create", student, f"Estudante criado: {student.full_name}")
        messages.success(request, "Estudante cadastrado.")
        return redirect("management:students")


class StudentUpdateView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(students_for_user(request.user, include_inactive=True), pk=pk)
        enrollment = student.current_enrollment()
        school = enrollment.school if enrollment else None
        if school and not can_write_school(request.user, school):
            return _forbidden(request)
        if not can_write_school(request.user):
            return _forbidden(request)
        form = StudentForm(instance=student, include_classroom=False)
        return render(
            request,
            "admin_panel/form.html",
            {"form": form, "page_title": f"Editar estudante — {student.full_name}", "cancel_url": "management:students"},
        )

    def post(self, request, pk):
        student = get_object_or_404(students_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user):
            return _forbidden(request)
        form = StudentForm(request.POST, instance=student, include_classroom=False)
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": f"Editar estudante — {student.full_name}", "cancel_url": "management:students"},
            )
        student = form.save()
        audit(request, "update", student, f"Estudante atualizado: {student.full_name}")
        messages.success(request, "Estudante atualizado.")
        return redirect("management:students")


class StudentArchiveView(ManagementRequiredMixin, View):
    def post(self, request, pk):
        student = get_object_or_404(students_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user):
            return _forbidden(request)
        if student.is_active:
            return archive_object(request, student, redirect_to="management:students")
        return restore_object(request, student, redirect_to="management:students")


class StudentDeleteView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(students_for_user(request.user, include_inactive=True), pk=pk)
        if not can_hard_delete(request.user):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/confirm_delete.html",
            {
                "object": student,
                "object_label": student.full_name,
                "cancel_url": "management:students",
                "warning": "Matrículas e avaliações vinculadas impedem exclusão. Prefira desativar.",
            },
        )

    def post(self, request, pk):
        student = get_object_or_404(students_for_user(request.user, include_inactive=True), pk=pk)
        return hard_delete_object(
            request,
            student,
            redirect_to="management:students",
            blocked=student.enrollments.exists(),
            block_message="O estudante possui matrículas. Desative-o em vez de excluir.",
        )


class EnrollmentCreateView(ManagementRequiredMixin, View):
    def get(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        form = EnrollmentForm(
            students=students_for_user(request.user, include_inactive=True),
            classrooms=classrooms_for_user(request.user),
        )
        return render(
            request,
            "admin_panel/form.html",
            {"form": form, "page_title": "Nova matrícula", "cancel_url": "management:enrollments"},
        )

    def post(self, request):
        if not can_write_school(request.user):
            return _forbidden(request)
        form = EnrollmentForm(
            request.POST,
            students=students_for_user(request.user, include_inactive=True),
            classrooms=classrooms_for_user(request.user),
        )
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": "Nova matrícula", "cancel_url": "management:enrollments"},
            )
        classroom = form.cleaned_data["classroom"]
        if not can_write_school(request.user, classroom.school):
            return _forbidden(request)
        enrollment = form.save()
        audit(request, "enrollment", enrollment, f"Matrícula criada: {enrollment}")
        messages.success(request, "Matrícula registrada.")
        return redirect("management:enrollments")


class EnrollmentUpdateView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        enrollment = get_object_or_404(enrollments_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, enrollment.school):
            return _forbidden(request)
        form = EnrollmentForm(
            instance=enrollment,
            students=students_for_user(request.user, include_inactive=True),
            classrooms=classrooms_for_user(request.user, include_inactive=True),
        )
        return render(
            request,
            "admin_panel/form.html",
            {"form": form, "page_title": f"Editar matrícula — {enrollment.student}", "cancel_url": "management:enrollments"},
        )

    def post(self, request, pk):
        enrollment = get_object_or_404(enrollments_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, enrollment.school):
            return _forbidden(request)
        form = EnrollmentForm(
            request.POST,
            instance=enrollment,
            students=students_for_user(request.user, include_inactive=True),
            classrooms=classrooms_for_user(request.user, include_inactive=True),
        )
        if not form.is_valid():
            return render(
                request,
                "admin_panel/form.html",
                {"form": form, "page_title": f"Editar matrícula — {enrollment.student}", "cancel_url": "management:enrollments"},
            )
        if not can_write_school(request.user, form.cleaned_data["classroom"].school):
            return _forbidden(request)
        enrollment = form.save()
        audit(request, "enrollment", enrollment, f"Matrícula atualizada: {enrollment}")
        messages.success(request, "Matrícula atualizada.")
        return redirect("management:enrollments")


class EnrollmentArchiveView(ManagementRequiredMixin, View):
    def post(self, request, pk):
        enrollment = get_object_or_404(enrollments_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, enrollment.school):
            return _forbidden(request)
        if enrollment.is_active:
            enrollment.status = Enrollment.Status.CANCELLED
            enrollment.save(update_fields=["status", "updated_at"])
            return archive_object(request, enrollment, redirect_to="management:enrollments")
        enrollment.status = Enrollment.Status.ACTIVE
        enrollment.save(update_fields=["status", "updated_at"])
        return restore_object(request, enrollment, redirect_to="management:enrollments")


class EnrollmentDeleteView(ManagementRequiredMixin, View):
    def get(self, request, pk):
        enrollment = get_object_or_404(enrollments_for_user(request.user, include_inactive=True), pk=pk)
        if not can_hard_delete(request.user) or not can_write_school(request.user, enrollment.school):
            return _forbidden(request)
        return render(
            request,
            "admin_panel/confirm_delete.html",
            {
                "object": enrollment,
                "object_label": str(enrollment),
                "cancel_url": "management:enrollments",
                "warning": "Sessões de avaliação nesta matrícula impedem exclusão. Prefira desativar.",
            },
        )

    def post(self, request, pk):
        enrollment = get_object_or_404(enrollments_for_user(request.user, include_inactive=True), pk=pk)
        if not can_write_school(request.user, enrollment.school):
            return _forbidden(request)
        return hard_delete_object(
            request,
            enrollment,
            redirect_to="management:enrollments",
            blocked=enrollment.assessment_sessions.exists(),
            block_message="Há avaliações nesta matrícula. Desative-a em vez de excluir.",
        )
