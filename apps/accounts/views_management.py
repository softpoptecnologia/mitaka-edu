"""Management (AdminLTE) views."""
from __future__ import annotations

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.models import Role, User, UserProfile
from apps.accounts.selectors import classrooms_for_user, schools_for_user, students_for_user
from apps.analytics.models import AggregatedIndicator, StudentSkillStatus
from apps.assessments.models import AssessmentInstrument
from apps.accounts.views_teachers import _filter_roles_for_user, _teachers_qs
from apps.core.permissions import ManagementRequiredMixin, NetworkRequiredMixin, cadastro_flags
from apps.curriculum.models import DevelopmentDimension, MatrixVersion, PedagogicalMatrix, Skill
from apps.interventions.models import ClassroomIntervention, StudentIntervention
from apps.schools.models import Classroom, Municipality, School, SchoolYear, TeacherClassroom
from apps.schools.services.school_year import activate_school_year, enroll_student_in_new_year
from apps.students.models import Enrollment, Student
from apps.students.services.import_csv import import_students_csv


class ManagementDashboardView(ManagementRequiredMixin, View):
    def get(self, request):
        from apps.assessments.models import AssessmentSession

        schools = schools_for_user(request.user)
        classrooms = classrooms_for_user(request.user)
        students = students_for_user(request.user)
        year = SchoolYear.objects.filter(is_active=True).first()
        attention_qs = StudentSkillStatus.objects.filter(student__in=students, needs_attention=True)
        attention_skills = attention_qs.values("skill__name").distinct().count()
        attention_students = attention_qs.values("student_id").distinct().count()
        total_enrollments = Enrollment.objects.filter(
            classroom__in=classrooms, school_year=year, is_active=True
        ).count() if year else 0
        assessed = (
            AssessmentSession.objects.filter(
                enrollment__classroom__in=classrooms,
                enrollment__school_year=year,
                status=AssessmentSession.Status.COMPLETED,
            )
            .values("enrollment_id")
            .distinct()
            .count()
            if year
            else 0
        )
        coverage = round(100 * assessed / total_enrollments, 1) if total_enrollments else 0
        school_rows = []
        school_labels = []
        school_attention_values = []
        for school in schools:
            school_students = students.filter(enrollments__classroom__school=school).distinct()
            att = (
                StudentSkillStatus.objects.filter(student__in=school_students, needs_attention=True)
                .values("student_id")
                .distinct()
                .count()
            )
            school_rows.append(
                {
                    "school": school,
                    "students": school_students.count(),
                    "attention": att,
                }
            )
            school_labels.append(school.name)
            school_attention_values.append(att)
        return render(
            request,
            "admin_panel/dashboard.html",
            {
                "schools_count": schools.count(),
                "classrooms_count": classrooms.count(),
                "students_count": students.count(),
                "attention_skills": attention_skills,
                "attention_students": attention_students,
                "coverage": coverage,
                "year": year,
                "schools": schools[:10],
                "school_rows": school_rows,
                "chart_school_labels": school_labels,
                "chart_school_attention": school_attention_values,
            },
        )


class SchoolListView(ManagementRequiredMixin, View):
    def get(self, request):
        include_inactive = request.GET.get("inativas") == "1"
        return render(
            request,
            "admin_panel/schools.html",
            {
                "schools": schools_for_user(request.user, include_inactive=include_inactive),
                "include_inactive": include_inactive,
                **cadastro_flags(request.user),
            },
        )


class ClassroomListView(ManagementRequiredMixin, View):
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        school_id = request.GET.get("escola")
        include_inactive = request.GET.get("inativas") == "1"
        qs = classrooms_for_user(request.user, include_inactive=include_inactive).select_related("school", "school_year")
        if q:
            qs = qs.filter(name__icontains=q)
        if school_id:
            qs = qs.filter(school_id=school_id)
        return render(
            request,
            "admin_panel/classrooms.html",
            {
                "classrooms": qs,
                "q": q,
                "school_id": school_id or "",
                "schools": schools_for_user(request.user),
                "include_inactive": include_inactive,
                **cadastro_flags(request.user),
            },
        )


class StudentListView(ManagementRequiredMixin, View):
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        school_id = request.GET.get("escola")
        atencao = request.GET.get("atencao") == "1"
        include_inactive = request.GET.get("inativas") == "1"
        qs = students_for_user(request.user, include_inactive=include_inactive)
        if q:
            qs = qs.filter(full_name__icontains=q) | students_for_user(
                request.user, include_inactive=include_inactive
            ).filter(external_code__icontains=q)
            qs = qs.distinct()
        if school_id:
            qs = qs.filter(enrollments__classroom__school_id=school_id).distinct()
        if atencao:
            attention_ids = StudentSkillStatus.objects.filter(needs_attention=True).values_list("student_id", flat=True)
            qs = qs.filter(id__in=attention_ids)
        return render(
            request,
            "admin_panel/students.html",
            {
                "students": qs.order_by("full_name"),
                "q": q,
                "school_id": school_id or "",
                "atencao": atencao,
                "schools": schools_for_user(request.user),
                "include_inactive": include_inactive,
                **cadastro_flags(request.user),
            },
        )


class EnrollmentListView(ManagementRequiredMixin, View):
    def get(self, request):
        from apps.accounts.selectors import enrollments_for_user

        q = (request.GET.get("q") or "").strip()
        status = request.GET.get("status", "")
        year_id = request.GET.get("ano")
        include_inactive = request.GET.get("inativas") == "1"
        qs = enrollments_for_user(request.user, include_inactive=include_inactive)
        if q:
            qs = qs.filter(student__full_name__icontains=q)
        if status:
            qs = qs.filter(status=status)
        if year_id:
            qs = qs.filter(school_year_id=year_id)
        return render(
            request,
            "admin_panel/enrollments.html",
            {
                "enrollments": qs,
                "q": q,
                "status": status,
                "year_id": year_id or "",
                "years": SchoolYear.objects.all().order_by("-year"),
                "status_choices": Enrollment.Status.choices,
                "include_inactive": include_inactive,
                **cadastro_flags(request.user),
            },
        )


class TeacherListView(ManagementRequiredMixin, View):
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        school_id = request.GET.get("escola")
        role_code = (request.GET.get("papel") or "").strip()
        include_inactive = request.GET.get("inativas") == "1"
        schools = schools_for_user(request.user)
        link_qs = TeacherClassroom.objects.select_related(
            "classroom", "classroom__school", "classroom__school_year"
        ).order_by("-is_primary", "classroom__name")
        qs = _teachers_qs(request.user).prefetch_related(Prefetch("teacher_classrooms", queryset=link_qs))
        if not include_inactive:
            qs = qs.filter(is_active=True)
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(username__icontains=q)
                | Q(email__icontains=q)
                | Q(userprofile__display_name__icontains=q)
            )
        if school_id:
            qs = qs.filter(userprofile__school_id=school_id)
        if role_code:
            qs = qs.filter(userprofile__role__code=role_code)
        teachers = list(qs)
        classroom_roles = {Role.Code.PROFESSOR, Role.Code.AEE}
        year = SchoolYear.objects.filter(is_active=True).first()
        attention_uncovered = 0
        if year:
            classroom_qs = classrooms_for_user(request.user).filter(school_year=year)
            if school_id:
                classroom_qs = classroom_qs.filter(school_id=school_id)
            linked_ids = TeacherClassroom.objects.filter(
                classroom_id__in=classroom_qs.values("id"),
                teacher__is_active=True,
                teacher__userprofile__role__code__in=[Role.Code.PROFESSOR, Role.Code.AEE],
            ).values_list("classroom_id", flat=True)
            uncovered_ids = list(classroom_qs.exclude(pk__in=linked_ids).values_list("id", flat=True))
            if uncovered_ids:
                attention_uncovered = (
                    StudentSkillStatus.objects.filter(
                        needs_attention=True,
                        student__is_active=True,
                        student__enrollments__is_active=True,
                        student__enrollments__school_year=year,
                        student__enrollments__classroom_id__in=uncovered_ids,
                    )
                    .values("student_id")
                    .distinct()
                    .count()
                )
        return render(
            request,
            "admin_panel/teachers.html",
            {
                "teachers": teachers,
                "q": q,
                "school_id": school_id or "",
                "role_code": role_code,
                "schools": schools,
                "roles": _filter_roles_for_user(request.user),
                "include_inactive": include_inactive,
                "attention_uncovered": attention_uncovered,
                "classroom_roles": tuple(classroom_roles),
                **cadastro_flags(request.user),
            },
        )


class MatrixListView(ManagementRequiredMixin, View):
    def get(self, request):
        matrices = PedagogicalMatrix.objects.prefetch_related("versions")
        return render(
            request,
            "admin_panel/matrix.html",
            {"matrices": matrices, **cadastro_flags(request.user)},
        )


class InstrumentListView(ManagementRequiredMixin, View):
    def get(self, request):
        instruments = AssessmentInstrument.objects.select_related("skill", "matrix_version")
        return render(
            request,
            "admin_panel/instruments.html",
            {"instruments": instruments, **cadastro_flags(request.user)},
        )


class IndicatorsView(ManagementRequiredMixin, View):
    def get(self, request):
        year_id = request.GET.get("ano")
        scope = request.GET.get("escopo", "")
        school_id = request.GET.get("escola")
        year = SchoolYear.objects.filter(pk=year_id).first() if year_id else SchoolYear.objects.filter(is_active=True).first()
        indicators = AggregatedIndicator.objects.filter(school_year=year).select_related(
            "school", "classroom", "skill"
        )
        if scope:
            indicators = indicators.filter(scope=scope)
        if school_id:
            indicators = indicators.filter(school_id=school_id)
        return render(
            request,
            "admin_panel/indicators.html",
            {
                "indicators": indicators[:200],
                "year": year,
                "years": SchoolYear.objects.all().order_by("-year"),
                "scope": scope,
                "school_id": school_id or "",
                "schools": schools_for_user(request.user),
                "scopes": AggregatedIndicator.Scope.choices,
            },
        )


class InterventionsListView(ManagementRequiredMixin, View):
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        status = request.GET.get("status", "")
        student_ints = StudentIntervention.objects.filter(is_active=True).select_related(
            "student", "skill", "responsible"
        ).order_by("-starts_on", "-created_at")
        class_ints = ClassroomIntervention.objects.filter(is_active=True).select_related(
            "classroom", "skill", "responsible"
        ).order_by("-starts_on", "-created_at")
        if q:
            student_ints = student_ints.filter(student__full_name__icontains=q)
            class_ints = class_ints.filter(classroom__name__icontains=q)
        if status:
            student_ints = student_ints.filter(status=status)
            class_ints = class_ints.filter(status=status)
        return render(
            request,
            "admin_panel/interventions.html",
            {
                "student_ints": student_ints[:80],
                "class_ints": class_ints[:80],
                "q": q,
                "status": status,
                **cadastro_flags(request.user),
            },
        )


class ImportStudentsView(ManagementRequiredMixin, View):
    def get(self, request):
        years = SchoolYear.objects.all()
        return render(request, "admin_panel/import_students.html", {"years": years})

    def post(self, request):
        year = get_object_or_404(SchoolYear, pk=request.POST.get("school_year"))
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Selecione um arquivo CSV.")
            return redirect("management:import_students")
        job = import_students_csv(file_obj=upload, school_year=year, created_by=request.user)
        messages.info(request, job.summary)
        return render(
            request,
            "admin_panel/import_students.html",
            {"years": SchoolYear.objects.all(), "job": job, "errors": job.errors.all()},
        )


class NewSchoolYearView(NetworkRequiredMixin, View):
    def get(self, request):
        years = SchoolYear.objects.all()
        classrooms = Classroom.objects.filter(is_active=True).select_related("school", "school_year")
        students = Student.objects.filter(is_active=True)
        return render(
            request,
            "admin_panel/new_year.html",
            {"years": years, "classrooms": classrooms, "students": students, **cadastro_flags(request.user)},
        )

    def post(self, request):
        action = request.POST.get("action")
        if action == "create_year":
            year = int(request.POST["year"])
            obj, created = SchoolYear.objects.get_or_create(year=year, defaults={"label": str(year)})
            if request.POST.get("activate"):
                activate_school_year(obj, actor=request.user)
            messages.success(request, f"Ano {year} {'criado' if created else 'atualizado'}.")
        elif action == "enroll":
            student = get_object_or_404(Student, pk=request.POST.get("student_id"))
            classroom = get_object_or_404(Classroom, pk=request.POST.get("classroom_id"))
            enroll_student_in_new_year(student=student, classroom=classroom, actor=request.user)
            messages.success(request, "Nova matrícula criada sem alterar histórico anterior.")
        return redirect("management:new_year")


class DimensionsSkillsView(ManagementRequiredMixin, View):
    def get(self, request):
        version = (
            MatrixVersion.objects.filter(is_published=True)
            .order_by("-published_at", "-id")
            .first()
        )
        dimensions = (
            DevelopmentDimension.objects.filter(matrix_version=version).prefetch_related("skills")
            if version
            else []
        )
        return render(
            request,
            "admin_panel/dimensions.html",
            {"version": version, "dimensions": dimensions, **cadastro_flags(request.user)},
        )
