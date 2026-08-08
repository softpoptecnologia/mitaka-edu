"""HTML + PDF pedagogical reports (same data, same pattern)."""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.accounts.selectors import (
    classrooms_for_user,
    schools_for_user,
    students_for_user,
    user_can_access_classroom,
    user_can_access_student,
)
from apps.analytics.services.scope import optional_pk
from apps.core.permissions import MANAGEMENT_ROLES, TeacherRequiredMixin, user_role_code
from apps.reports.services import (
    build_classroom_pdf,
    build_network_pdf,
    build_school_pdf,
    build_student_pdf,
    classroom_report_data,
    network_report_data,
    school_report_data,
    student_report_data,
)
from apps.curriculum.models import Skill
from apps.schools.models import Classroom, Municipality, School, SchoolYear
from apps.students.models import Student


class ReportAccessMixin(TeacherRequiredMixin):
    """Professor, AEE, gestão e rede podem gerar relatórios no respectivo escopo."""

    allowed_roles = ("PROFESSOR",) + MANAGEMENT_ROLES


def _pdf_response(content: bytes, filename: str) -> HttpResponse:
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class ReportIndexView(ReportAccessMixin, View):
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        students = students_for_user(request.user)
        if q:
            students = students.filter(full_name__icontains=q) | students.filter(external_code__icontains=q)
        return render(
            request,
            "admin_panel/reports_index.html",
            {
                "schools": schools_for_user(request.user),
                "classrooms": classrooms_for_user(request.user),
                "students": students.distinct().order_by("full_name")[:200],
                "q": q,
            },
        )


class StudentReportView(ReportAccessMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        if not user_can_access_student(request.user, student) and user_role_code(request.user) not in {
            "SUPERADMIN",
            "SECRETARIA",
            "TECNICO",
        }:
            return render(request, "admin_panel/forbidden.html", status=403)
        data = student_report_data(student)
        if request.GET.get("formato") == "pdf":
            filename = f"relatorio-estudante-{student.external_code or student.pk}.pdf"
            return _pdf_response(build_student_pdf(data), filename)
        return render(request, "admin_panel/report_student.html", data)


class ClassroomReportView(ReportAccessMixin, View):
    def get(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        if not user_can_access_classroom(request.user, classroom) and user_role_code(request.user) not in {
            "SUPERADMIN",
            "SECRETARIA",
            "TECNICO",
        }:
            return render(request, "admin_panel/forbidden.html", status=403)
        data = classroom_report_data(classroom)
        if request.GET.get("formato") == "pdf":
            filename = f"relatorio-turma-{classroom.pk}.pdf"
            return _pdf_response(build_classroom_pdf(data), filename)
        return render(request, "admin_panel/report_classroom.html", data)


class SchoolReportView(ReportAccessMixin, View):
    def get(self, request, pk):
        school = get_object_or_404(School, pk=pk)
        year_id = optional_pk(request.GET.get("ano"))
        year = SchoolYear.objects.filter(pk=year_id).first() if year_id else SchoolYear.objects.filter(is_active=True).first()
        classroom_id = optional_pk(request.GET.get("turma"))
        skill_id = optional_pk(request.GET.get("habilidade"))
        classroom = Classroom.objects.filter(pk=classroom_id, school=school).first() if classroom_id else None
        skill = Skill.objects.filter(pk=skill_id).first() if skill_id else None
        data = school_report_data(school, year=year, classroom=classroom, skill=skill)
        if request.GET.get("formato") == "pdf":
            filename = f"relatorio-escola-{school.code}.pdf"
            return _pdf_response(build_school_pdf(data), filename)
        return render(request, "admin_panel/report_school.html", data)


class NetworkReportView(ReportAccessMixin, View):
    def get(self, request):
        municipality = Municipality.objects.first()
        year_id = optional_pk(request.GET.get("ano"))
        year = SchoolYear.objects.filter(pk=year_id).first() if year_id else SchoolYear.objects.filter(is_active=True).first()
        data = network_report_data(municipality=municipality, year=year)
        if request.GET.get("formato") == "pdf":
            return _pdf_response(build_network_pdf(data), "relatorio-rede.pdf")
        data["years"] = SchoolYear.objects.all().order_by("-year")
        return render(request, "admin_panel/report_network.html", data)
