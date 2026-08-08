"""Secretaria municipal dashboards."""
from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.analytics.services.scope import build_secretaria_snapshot, optional_pk, parse_secretaria_filters
from apps.core.permissions import NetworkRequiredMixin
from apps.reports.services.pdf import build_secretaria_pdf
from apps.schools.models import Classroom, School, SchoolYear


class SecretariaDashboardView(NetworkRequiredMixin, View):
    def get(self, request):
        filters = parse_secretaria_filters(request)
        snapshot = build_secretaria_snapshot(filters)
        if request.GET.get("formato") == "pdf":
            filename = "relatorio-secretaria.pdf"
            if filters.school:
                filename = f"relatorio-secretaria-{filters.school.code}.pdf"
            response = HttpResponse(build_secretaria_pdf(snapshot), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        return render(request, "admin_panel/secretaria_dashboard.html", snapshot)


class SchoolCompareView(NetworkRequiredMixin, View):
    def get(self, request):
        filters = parse_secretaria_filters(request)
        snapshot = build_secretaria_snapshot(filters)
        if request.GET.get("formato") == "pdf":
            response = HttpResponse(build_secretaria_pdf(snapshot), content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="comparacao-escolas.pdf"'
            return response
        return render(request, "admin_panel/school_compare.html", snapshot)


class PedagogicalNeedsView(NetworkRequiredMixin, View):
    def get(self, request):
        filters = parse_secretaria_filters(request)
        snapshot = build_secretaria_snapshot(filters)
        if request.GET.get("formato") == "pdf":
            response = HttpResponse(build_secretaria_pdf(snapshot), content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="necessidades-pedagogicas.pdf"'
            return response
        return render(request, "admin_panel/pedagogical_needs.html", snapshot)


class DrillDownView(NetworkRequiredMixin, View):
    def get(self, request):
        filters = parse_secretaria_filters(request)
        snapshot = build_secretaria_snapshot(filters)
        if request.GET.get("formato") == "pdf":
            response = HttpResponse(build_secretaria_pdf(snapshot), content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="navegacao-rede.pdf"'
            return response
        school_id = optional_pk(request.GET.get("escola"))
        classroom_id = optional_pk(request.GET.get("turma"))
        year = filters.year or SchoolYear.objects.filter(is_active=True).first()
        context = {**snapshot, "year": year, "level": "rede"}
        if classroom_id:
            classroom = get_object_or_404(Classroom, pk=classroom_id)
            enrollments = classroom.enrollments.filter(is_active=True).select_related("student")
            context.update({"level": "turma", "classroom": classroom, "enrollments": enrollments})
        elif school_id:
            school = get_object_or_404(School, pk=school_id)
            classrooms = school.classrooms.filter(is_active=True, school_year=year) if year else school.classrooms.none()
            context.update({"level": "escola", "school": school, "classrooms": classrooms})
        else:
            context["drill_schools"] = School.objects.filter(is_active=True)
        return render(request, "admin_panel/drilldown.html", context)
