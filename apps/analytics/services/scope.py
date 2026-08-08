"""Secretaria recorte: filtros compartilhados entre painel, páginas e PDF."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from django.db.models import Count, Q

from apps.analytics.models import StudentSkillStatus
from apps.analytics.services.accessibility_indicators import network_accessibility_stats
from apps.assessments.models import AssessmentSession
from apps.curriculum.models import Skill
from apps.schools.models import Classroom, Municipality, School, SchoolYear
from apps.students.models import Enrollment


@dataclass
class SecretariaFilters:
    year: SchoolYear | None
    school: School | None
    classroom: Classroom | None
    grade: str
    skill: Skill | None
    recorte: str  # all | atencao | acesso
    municipality: Municipality | None

    def querydict(self) -> dict[str, str]:
        data = {}
        if self.year:
            data["ano"] = str(self.year.pk)
        if self.school:
            data["escola"] = str(self.school.pk)
        if self.classroom:
            data["turma"] = str(self.classroom.pk)
        if self.grade:
            data["serie"] = self.grade
        if self.skill:
            data["habilidade"] = str(self.skill.pk)
        if self.recorte and self.recorte != "all":
            data["recorte"] = self.recorte
        return data

    def querystring(self) -> str:
        return urlencode(self.querydict())

    def scope_label(self) -> str:
        parts = []
        if self.municipality:
            parts.append(f"{self.municipality.name}/{self.municipality.state}")
        if self.year:
            parts.append(str(self.year))
        if self.school:
            parts.append(self.school.name)
        if self.classroom:
            parts.append(self.classroom.name)
        if self.grade:
            parts.append(self.grade)
        if self.skill:
            parts.append(self.skill.name)
        if self.recorte == "atencao":
            parts.append("somente atenção")
        elif self.recorte == "acesso":
            parts.append("somente com recurso de acesso")
        return " · ".join(parts) or "Rede municipal"

    def recorte_label(self) -> str:
        return {
            "all": "Toda a rede no recorte",
            "atencao": "Somente estudantes em atenção",
            "acesso": "Somente sessões com recurso de acesso",
        }.get(self.recorte, "Toda a rede no recorte")


def optional_pk(value) -> int | None:
    """Selects submit '' when 'Todas' is chosen — never pass that to pk=."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def parse_secretaria_filters(request) -> SecretariaFilters:
    municipality = Municipality.objects.first()
    year_id = optional_pk(request.GET.get("ano"))
    year = (
        SchoolYear.objects.filter(pk=year_id).first()
        if year_id
        else SchoolYear.objects.filter(is_active=True).first()
    )
    school_id = optional_pk(request.GET.get("escola"))
    classroom_id = optional_pk(request.GET.get("turma"))
    skill_id = optional_pk(request.GET.get("habilidade"))
    school = School.objects.filter(pk=school_id, is_active=True).first() if school_id else None
    classroom = (
        Classroom.objects.filter(pk=classroom_id, is_active=True).select_related("school").first()
        if classroom_id
        else None
    )
    if classroom and not school:
        school = classroom.school
    if classroom and year and classroom.school_year_id != year.pk:
        classroom = None
    if classroom and school and classroom.school_id != school.pk:
        classroom = None
    grade = (request.GET.get("serie") or "").strip()
    skill = Skill.objects.filter(pk=skill_id).select_related("dimension").first() if skill_id else None
    recorte = request.GET.get("recorte") or "all"
    if recorte not in {"all", "atencao", "acesso"}:
        recorte = "all"
    return SecretariaFilters(
        year=year,
        school=school,
        classroom=classroom,
        grade=grade,
        skill=skill,
        recorte=recorte,
        municipality=municipality,
    )


def enrollments_for_filters(filters: SecretariaFilters):
    qs = Enrollment.objects.filter(is_active=True).select_related(
        "student", "classroom", "classroom__school", "school_year"
    )
    if filters.year:
        qs = qs.filter(school_year=filters.year)
    if filters.classroom:
        qs = qs.filter(classroom=filters.classroom)
    elif filters.school:
        qs = qs.filter(classroom__school=filters.school)
    elif filters.municipality:
        qs = qs.filter(classroom__school__municipality=filters.municipality)
    if filters.grade:
        qs = qs.filter(classroom__grade_label=filters.grade)
    return qs


def _apply_recorte(enrollments, filters: SecretariaFilters):
    if filters.recorte == "atencao":
        ids = StudentSkillStatus.objects.filter(
            enrollment__in=enrollments, needs_attention=True
        ).values_list("enrollment_id", flat=True)
        if filters.skill:
            ids = StudentSkillStatus.objects.filter(
                enrollment__in=enrollments, needs_attention=True, skill=filters.skill
            ).values_list("enrollment_id", flat=True)
        return enrollments.filter(pk__in=ids)
    if filters.recorte == "acesso":
        ids = (
            AssessmentSession.objects.filter(enrollment__in=enrollments)
            .exclude(active_features=[])
            .values_list("enrollment_id", flat=True)
        )
        return enrollments.filter(pk__in=ids)
    return enrollments


def build_secretaria_snapshot(filters: SecretariaFilters) -> dict:
    base_enrollments = enrollments_for_filters(filters)
    enrollments = _apply_recorte(base_enrollments, filters)
    enrollment_ids = list(enrollments.values_list("id", flat=True))
    student_ids = list(enrollments.values_list("student_id", flat=True).distinct())

    classrooms_qs = Classroom.objects.filter(is_active=True)
    if filters.year:
        classrooms_qs = classrooms_qs.filter(school_year=filters.year)
    if filters.school:
        classrooms_qs = classrooms_qs.filter(school=filters.school)
    if filters.grade:
        classrooms_qs = classrooms_qs.filter(grade_label=filters.grade)
    if filters.classroom:
        classrooms_qs = classrooms_qs.filter(pk=filters.classroom.pk)

    schools_qs = School.objects.filter(is_active=True)
    if filters.municipality:
        schools_qs = schools_qs.filter(municipality=filters.municipality)
    if filters.school:
        schools_qs = schools_qs.filter(pk=filters.school.pk)

    statuses = StudentSkillStatus.objects.filter(enrollment_id__in=enrollment_ids).select_related("skill", "student")
    if filters.skill:
        statuses = statuses.filter(skill=filters.skill)

    attention_students = statuses.filter(needs_attention=True).values("student_id").distinct().count()
    assessed = (
        AssessmentSession.objects.filter(
            enrollment_id__in=enrollment_ids,
            status=AssessmentSession.Status.COMPLETED,
        )
        .values("enrollment_id")
        .distinct()
        .count()
    )
    total = enrollments.distinct().count()
    coverage = round(100 * assessed / total, 1) if total else 0.0

    skill_rows = []
    skill_qs = (
        statuses.values("skill_id", "skill__name", "skill__bncc_code")
        .annotate(
            sample=Count("id"),
            attention=Count("id", filter=Q(needs_attention=True)),
        )
        .order_by("-attention", "skill__name")
    )
    for row in skill_qs:
        sample = row["sample"] or 0
        attention = row["attention"] or 0
        pct = round(100.0 * attention / sample, 1) if sample else 0.0
        skill_rows.append(
            {
                "skill_id": row["skill_id"],
                "name": row["skill__name"],
                "bncc_code": row["skill__bncc_code"] or "",
                "sample": sample,
                "attention": attention,
                "pct": pct,
            }
        )

    ranking = []
    if filters.classroom:
        ranking_title = "Estudantes no recorte"
        for enrollment in enrollments.select_related("student").order_by("student__full_name")[:40]:
            st = [s for s in statuses if s.student_id == enrollment.student_id]
            needs = any(s.needs_attention for s in st)
            ranking.append(
                {
                    "label": enrollment.student.full_name,
                    "detail": enrollment.student.external_code or "",
                    "value": "Atenção" if needs else "Regular",
                    "pct": 100 if needs else 0,
                }
            )
    elif filters.school:
        ranking_title = "Turmas — atenção"
        for room in classrooms_qs.select_related("school"):
            room_enr = enrollments.filter(classroom=room)
            room_ids = list(room_enr.values_list("id", flat=True))
            sample = room_enr.count()
            att = (
                StudentSkillStatus.objects.filter(enrollment_id__in=room_ids, needs_attention=True)
                .values("student_id")
                .distinct()
                .count()
            )
            pct = round(100.0 * att / sample, 1) if sample else 0.0
            ranking.append({"label": room.name, "detail": room.grade_label, "value": f"{att}/{sample}", "pct": pct})
        ranking.sort(key=lambda r: r["pct"], reverse=True)
    else:
        ranking_title = "Escolas — atenção"
        for school in schools_qs:
            school_enr = enrollments.filter(classroom__school=school)
            sample = school_enr.values("student_id").distinct().count()
            att = (
                StudentSkillStatus.objects.filter(
                    enrollment__in=school_enr, needs_attention=True
                )
                .values("student_id")
                .distinct()
                .count()
            )
            pct = round(100.0 * att / sample, 1) if sample else 0.0
            ranking.append({"label": school.name, "detail": school.code, "value": f"{att}/{sample}", "pct": pct})
        ranking.sort(key=lambda r: r["pct"], reverse=True)

    a11y = network_accessibility_stats(
        school_year=filters.year,
        school=filters.school,
        classroom=filters.classroom,
        enrollment_ids=enrollment_ids,
    )

    grade_choices = (
        Classroom.objects.filter(is_active=True, school_year=filters.year)
        .order_by("grade_label")
        .values_list("grade_label", flat=True)
        .distinct()
        if filters.year
        else []
    )
    if filters.school:
        grade_choices = (
            Classroom.objects.filter(is_active=True, school=filters.school, school_year=filters.year)
            .order_by("grade_label")
            .values_list("grade_label", flat=True)
            .distinct()
        )

    classroom_choices = Classroom.objects.none()
    if filters.school and filters.year:
        classroom_choices = Classroom.objects.filter(
            is_active=True, school=filters.school, school_year=filters.year
        ).order_by("name")

    return {
        "filters": filters,
        "filter_qs": filters.querystring(),
        "scope_label": filters.scope_label(),
        "recorte_label": filters.recorte_label(),
        "municipality": filters.municipality,
        "year": filters.year,
        "years": SchoolYear.objects.all().order_by("-year"),
        "schools": School.objects.filter(is_active=True, municipality=filters.municipality).order_by("name")
        if filters.municipality
        else School.objects.filter(is_active=True).order_by("name"),
        "classroom_choices": classroom_choices,
        "grade_choices": list(grade_choices),
        "skills": Skill.objects.select_related("dimension").order_by("dimension__order", "order", "name"),
        "schools_count": schools_qs.count(),
        "classrooms_count": classrooms_qs.count(),
        "students_count": len(set(student_ids)),
        "enrollments_count": total,
        "attention_students": attention_students,
        "coverage": coverage,
        "skill_rows": skill_rows,
        "ranking": ranking[:12],
        "ranking_title": ranking_title,
        "a11y_stats": a11y,
        "chart_skill_labels": [r["name"] for r in skill_rows[:8]],
        "chart_skill_values": [r["pct"] for r in skill_rows[:8]],
        "chart_rank_labels": [r["label"] for r in ranking[:8]],
        "chart_rank_values": [r["pct"] for r in ranking[:8]],
    }
