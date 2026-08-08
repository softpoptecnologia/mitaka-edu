from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.assessments.models import AssessmentInstrument, AssessmentItem, AssessmentOption
from apps.curriculum.models import DevelopmentDimension, MatrixVersion, PedagogicalMatrix, Skill
from apps.analytics.models import AggregatedIndicator, StudentSkillStatus
from apps.analytics.services.scope import build_secretaria_snapshot, parse_secretaria_filters
from apps.reports.services import build_secretaria_pdf, build_school_pdf, build_student_pdf, student_report_data
from apps.reports.services.context import school_report_data
from apps.schools.models import Classroom, Municipality, School, SchoolYear, TeacherClassroom
from apps.students.models import Enrollment, Student

User = get_user_model()


class PdfReportTests(TestCase):
    def setUp(self):
        for code, name in Role.Code.choices:
            Role.objects.get_or_create(code=code, defaults={"name": name})
        self.muni = Municipality.objects.create(name="Jucati", slug="jucati-pdf", state="PE")
        self.year = SchoolYear.objects.create(year=2026, label="2026", is_active=True)
        self.school = School.objects.create(municipality=self.muni, name="Escola PDF", code="PDF1")
        self.classroom = Classroom.objects.create(
            school=self.school, school_year=self.year, name="Turma PDF", grade_label="Infantil V"
        )
        self.professor = User.objects.create_user(username="prof_pdf", password="pass12345", first_name="Ana")
        profile = self.professor.userprofile
        profile.role = Role.objects.get(code=Role.Code.PROFESSOR)
        profile.school = self.school
        profile.save()
        TeacherClassroom.objects.create(teacher=self.professor, classroom=self.classroom)
        self.student = Student.objects.create(
            full_name="Luna Relatório", external_code="PDF001", birth_date=date(2020, 1, 1)
        )
        Enrollment.objects.create(student=self.student, classroom=self.classroom, school_year=self.year)
        matrix = PedagogicalMatrix.objects.create(name="Matriz PDF")
        version = MatrixVersion.objects.create(
            matrix=matrix, version_label="v1", is_published=True, published_at=timezone.now()
        )
        dim = DevelopmentDimension.objects.create(matrix_version=version, code="rimas", name="Rimas")
        skill = Skill.objects.create(dimension=dim, code="rimas_pdf", name="Rimas")
        inst = AssessmentInstrument.objects.create(
            matrix_version=version,
            skill=skill,
            title="Sondagem PDF",
            instrument_type=AssessmentInstrument.InstrumentType.DIGITAL,
        )
        item = AssessmentItem.objects.create(
            instrument=inst, order=1, item_type=AssessmentItem.ItemType.SINGLE_SELECT, prompt="Rima?"
        )
        AssessmentOption.objects.create(item=item, label="OK", score_value=1, is_correct=True, order=1)

    def test_student_pdf_starts_with_pdf_header(self):
        data = student_report_data(self.student)
        content = build_student_pdf(data)
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 500)

    def test_teacher_can_download_student_pdf(self):
        client = self.client
        client.login(username="prof_pdf", password="pass12345")
        response = client.get(reverse("management:report_student", args=[self.student.pk]) + "?formato=pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))


class SecretariaPdfFilterTests(TestCase):
    def setUp(self):
        for code, name in Role.Code.choices:
            Role.objects.get_or_create(code=code, defaults={"name": name})
        self.muni = Municipality.objects.create(name="Jucati", slug="jucati-sec", state="PE")
        self.year = SchoolYear.objects.create(year=2026, label="2026", is_active=True)
        self.school_a = School.objects.create(municipality=self.muni, name="Escola A", code="SECA")
        self.school_b = School.objects.create(municipality=self.muni, name="Escola B", code="SECB")
        room_a = Classroom.objects.create(
            school=self.school_a, school_year=self.year, name="Turma A", grade_label="Infantil V"
        )
        room_b = Classroom.objects.create(
            school=self.school_b, school_year=self.year, name="Turma B", grade_label="1º Ano"
        )
        student_a = Student.objects.create(full_name="Aluno A", external_code="SECA01", birth_date=date(2020, 1, 1))
        student_b = Student.objects.create(full_name="Aluno B", external_code="SECB01", birth_date=date(2020, 2, 1))
        Enrollment.objects.create(student=student_a, classroom=room_a, school_year=self.year)
        Enrollment.objects.create(student=student_b, classroom=room_b, school_year=self.year)
        self.secretaria = User.objects.create_user(username="sec_pdf", password="pass12345")
        profile = self.secretaria.userprofile
        profile.role = Role.objects.get(code=Role.Code.SECRETARIA)
        profile.save()

    def test_empty_filter_values_do_not_crash(self):
        self.client.login(username="sec_pdf", password="pass12345")
        url = (
            reverse("secretaria:dashboard")
            + f"?ano={self.year.pk}&escola={self.school_a.pk}&serie=&habilidade=&recorte=all"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        from django.test import RequestFactory

        request = RequestFactory().get(
            "/secretaria/",
            {"ano": str(self.year.pk), "escola": str(self.school_a.pk), "serie": "", "habilidade": "", "turma": ""},
        )
        filters = parse_secretaria_filters(request)
        self.assertEqual(filters.school, self.school_a)
        self.assertIsNone(filters.skill)
        self.assertIsNone(filters.classroom)

    def test_pdf_respects_school_filter(self):
        from django.test import RequestFactory

        factory = RequestFactory()
        request_all = factory.get("/secretaria/")
        snap_all = build_secretaria_snapshot(parse_secretaria_filters(request_all))
        request_a = factory.get("/secretaria/", {"escola": str(self.school_a.pk), "ano": str(self.year.pk)})
        snap_a = build_secretaria_snapshot(parse_secretaria_filters(request_a))
        self.assertEqual(snap_a["students_count"], 1)
        self.assertGreaterEqual(snap_all["students_count"], snap_a["students_count"])
        pdf = build_secretaria_pdf(snap_a)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_secretaria_can_download_filtered_pdf(self):
        client = self.client
        client.login(username="sec_pdf", password="pass12345")
        url = reverse("secretaria:dashboard") + f"?ano={self.year.pk}&escola={self.school_a.pk}&formato=pdf"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_compare_and_needs_pdf_use_same_filters(self):
        self.client.login(username="sec_pdf", password="pass12345")
        qs = f"?ano={self.year.pk}&escola={self.school_a.pk}&formato=pdf"
        for name in ("secretaria:compare", "secretaria:needs", "secretaria:drilldown"):
            response = self.client.get(reverse(name) + qs)
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual(response["Content-Type"], "application/pdf")
            self.assertTrue(response.content.startswith(b"%PDF"))


class SchoolReportCoherenceTests(TestCase):
    def setUp(self):
        for code, name in Role.Code.choices:
            Role.objects.get_or_create(code=code, defaults={"name": name})
        self.muni = Municipality.objects.create(name="Jucati", slug="jucati-esc", state="PE")
        self.year = SchoolYear.objects.create(year=2026, label="2026", is_active=True)
        self.school = School.objects.create(municipality=self.muni, name="EMEI Teste", code="ESC002T")
        self.room_a = Classroom.objects.create(
            school=self.school, school_year=self.year, name="Infantil V A", grade_label="Infantil V"
        )
        self.room_b = Classroom.objects.create(
            school=self.school, school_year=self.year, name="1º Ano A", grade_label="1º Ano"
        )
        matrix = PedagogicalMatrix.objects.create(name="Matriz Esc")
        version = MatrixVersion.objects.create(
            matrix=matrix, version_label="v1", is_published=True, published_at=timezone.now()
        )
        dim = DevelopmentDimension.objects.create(matrix_version=version, code="rimas", name="Rimas")
        self.skill = Skill.objects.create(dimension=dim, code="EF12LP07PE", name="Identificar rimas", bncc_code="EF12LP07PE")
        for i in range(5):
            sa = Student.objects.create(full_name=f"Aluno A{i}", external_code=f"A{i:03d}", birth_date=date(2020, 1, 1))
            sb = Student.objects.create(full_name=f"Aluno B{i}", external_code=f"B{i:03d}", birth_date=date(2020, 2, 1))
            ea = Enrollment.objects.create(student=sa, classroom=self.room_a, school_year=self.year)
            eb = Enrollment.objects.create(student=sb, classroom=self.room_b, school_year=self.year)
            StudentSkillStatus.objects.create(
                student=sa, skill=self.skill, enrollment=ea, status_code="needs_support",
                status_label="Atenção", needs_attention=True,
            )
            StudentSkillStatus.objects.create(
                student=sb, skill=self.skill, enrollment=eb, status_code="developing",
                status_label="Em desenvolvimento", needs_attention=False,
            )
        AggregatedIndicator.objects.create(
            scope=AggregatedIndicator.Scope.CLASSROOM, school_year=self.year, municipality=self.muni,
            school=self.school, classroom=self.room_a, skill=self.skill, metric_key="attention_pct",
            metric_value=100.0, sample_size=5,
        )
        AggregatedIndicator.objects.create(
            scope=AggregatedIndicator.Scope.CLASSROOM, school_year=self.year, municipality=self.muni,
            school=self.school, classroom=self.room_b, skill=self.skill, metric_key="attention_pct",
            metric_value=0.0, sample_size=5,
        )
        AggregatedIndicator.objects.create(
            scope=AggregatedIndicator.Scope.SCHOOL, school_year=self.year, municipality=self.muni,
            school=self.school, skill=self.skill, metric_key="attention_pct",
            metric_value=50.0, sample_size=10,
        )
        self.secretaria = User.objects.create_user(username="sec_esc", password="pass12345")
        profile = self.secretaria.userprofile
        profile.role = Role.objects.get(code=Role.Code.SECRETARIA)
        profile.save()

    def test_school_and_classroom_rows_are_not_mixed(self):
        data = school_report_data(self.school, year=self.year)
        self.assertEqual(len(data["school_indicators"]), 1)
        self.assertEqual(data["school_indicators"][0].metric_value, 50.0)
        self.assertEqual(data["school_indicators"][0].sample_size, 10)
        self.assertEqual(len(data["classroom_indicators"]), 2)
        by_room = {i.classroom_id: i for i in data["classroom_indicators"]}
        self.assertEqual(by_room[self.room_a.pk].metric_value, 100.0)
        self.assertEqual(by_room[self.room_b.pk].metric_value, 0.0)
        self.assertEqual(data["attention_students"], 5)
        self.assertEqual(data["students_count"], 10)

    def test_classroom_filter_hides_school_rollup(self):
        data = school_report_data(self.school, year=self.year, classroom=self.room_a)
        self.assertEqual(data["school_indicators"], [])
        self.assertEqual(len(data["classroom_indicators"]), 1)
        self.assertEqual(data["classroom_indicators"][0].classroom_id, self.room_a.pk)
        self.assertEqual(data["students_count"], 5)
        self.assertEqual(data["attention_students"], 5)
        pdf = build_school_pdf(data)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_html_report_does_not_repeat_skill_without_scope(self):
        self.client.login(username="sec_esc", password="pass12345")
        response = self.client.get(reverse("management:report_school", args=[self.school.pk]))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Escola — % em atenção por habilidade", html)
        self.assertIn("Turmas — % em atenção por habilidade", html)
        self.assertEqual(html.count("Identificar rimas"), 4)  # filtro + escola + 2 turmas
