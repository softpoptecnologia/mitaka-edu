"""Critical MVP tests."""
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, UserProfile
from apps.accounts.selectors import classrooms_for_user, schools_for_user
from apps.assessments.models import (
    AssessmentInstrument,
    AssessmentItem,
    AssessmentOption,
    AssessmentSession,
    ScoringRule,
)
from apps.assessments.services import complete_session, save_response, start_session
from apps.assessments.services.scoring import score_session
from apps.curriculum.models import DevelopmentDimension, MatrixVersion, PedagogicalMatrix, Skill, StatusLabelConfig
from apps.accessibility.models import StudentSupportPlan
from apps.interventions.models import InterventionStatus, InterventionTemplate, StudentIntervention
from apps.interventions.services.recommend import recommend_template_for_result
from apps.schools.models import Classroom, Municipality, School, SchoolYear, TeacherClassroom
from apps.schools.services.school_year import enroll_student_in_new_year
from apps.students.models import Enrollment, Student
from apps.students.services.import_csv import import_students_csv

User = get_user_model()


class BaseFixtureTestCase(TestCase):
    def setUp(self):
        for code, name in Role.Code.choices:
            Role.objects.get_or_create(code=code, defaults={"name": name})
        self.municipality = Municipality.objects.create(name="Jucati", slug="jucati", state="PE")
        self.year = SchoolYear.objects.create(year=2026, label="2026", is_active=True)
        self.year_next = SchoolYear.objects.create(year=2027, label="2027", is_active=False)
        self.school_a = School.objects.create(municipality=self.municipality, name="Escola A", code="A1")
        self.school_b = School.objects.create(municipality=self.municipality, name="Escola B", code="B1")
        self.classroom_a = Classroom.objects.create(
            school=self.school_a, school_year=self.year, name="Infantil V A", grade_label="Infantil V"
        )
        self.classroom_b = Classroom.objects.create(
            school=self.school_b, school_year=self.year, name="Infantil V A", grade_label="Infantil V"
        )
        self.classroom_next = Classroom.objects.create(
            school=self.school_a, school_year=self.year_next, name="1º Ano A", grade_label="1º Ano"
        )

        self.professor = self._user("prof1", Role.Code.PROFESSOR, self.school_a)
        self.professor_other = self._user("prof2", Role.Code.PROFESSOR, self.school_b)
        self.gestor = self._user("gestor1", Role.Code.GESTOR, self.school_a)
        self.gestor_b = self._user("gestor2", Role.Code.GESTOR, self.school_b)
        TeacherClassroom.objects.create(teacher=self.professor, classroom=self.classroom_a)
        TeacherClassroom.objects.create(teacher=self.professor_other, classroom=self.classroom_b)

        self.student = Student.objects.create(full_name="Criança Teste", external_code="T001", birth_date=date(2020, 5, 1))
        self.enrollment = Enrollment.objects.create(
            student=self.student, classroom=self.classroom_a, school_year=self.year
        )

        self.matrix = PedagogicalMatrix.objects.create(name="Matriz Teste")
        self.version = MatrixVersion.objects.create(
            matrix=self.matrix, version_label="v1", is_published=True, published_at=timezone.now()
        )
        self.version2 = MatrixVersion.objects.create(matrix=self.matrix, version_label="v2", is_published=False)
        dim = DevelopmentDimension.objects.create(matrix_version=self.version, code="rimas", name="Rimas")
        self.skill = Skill.objects.create(dimension=dim, code="rimas_base", name="Reconhecer rimas")
        StatusLabelConfig.objects.create(matrix_version=self.version, code="developing", label="Em desenvolvimento")
        StatusLabelConfig.objects.create(matrix_version=self.version, code="needs_support", label="Necessita maior mediação")
        StatusLabelConfig.objects.create(matrix_version=self.version, code="demonstrated", label="Habilidade demonstrada")

        self.instrument = AssessmentInstrument.objects.create(
            matrix_version=self.version,
            skill=self.skill,
            title="Sondagem rimas",
            instrument_type=AssessmentInstrument.InstrumentType.DIGITAL,
        )
        self.item = AssessmentItem.objects.create(
            instrument=self.instrument,
            order=1,
            item_type=AssessmentItem.ItemType.SINGLE_SELECT,
            prompt="Qual rima?",
        )
        self.opt_ok = AssessmentOption.objects.create(item=self.item, label="OK", score_value=1, is_correct=True, order=1)
        self.opt_bad = AssessmentOption.objects.create(item=self.item, label="NO", score_value=0, is_correct=False, order=2)
        ScoringRule.objects.create(
            instrument=self.instrument,
            skill=self.skill,
            min_score=0,
            max_score=0,
            result_code="needs_support",
            status_code="needs_support",
            label="Necessita maior mediação",
        )
        ScoringRule.objects.create(
            instrument=self.instrument,
            skill=self.skill,
            min_score=1,
            max_score=1,
            result_code="demonstrated",
            status_code="demonstrated",
            label="Habilidade demonstrada",
        )
        InterventionTemplate.objects.create(
            skill=self.skill,
            title="Fortalecer rimas",
            objective="Objetivo",
            suggested_activities="Jogo\nParlenda",
        )

    def _user(self, username, role_code, school):
        user = User.objects.create_user(username=username, password="pass12345", first_name=username)
        profile = user.userprofile
        profile.role = Role.objects.get(code=role_code)
        profile.school = school
        profile.save()
        return user


class PermissionTests(BaseFixtureTestCase):
    def test_professor_cannot_access_other_classroom(self):
        self.assertTrue(classrooms_for_user(self.professor).filter(pk=self.classroom_a.pk).exists())
        self.assertFalse(classrooms_for_user(self.professor).filter(pk=self.classroom_b.pk).exists())
        client = Client()
        client.login(username="prof1", password="pass12345")
        response = client.get(reverse("teacher:classroom", args=[self.classroom_b.pk]))
        self.assertEqual(response.status_code, 302)

    def test_gestor_cannot_access_other_school(self):
        self.assertTrue(schools_for_user(self.gestor).filter(pk=self.school_a.pk).exists())
        self.assertFalse(schools_for_user(self.gestor).filter(pk=self.school_b.pk).exists())


class SidebarNavTests(BaseFixtureTestCase):
    def _sidebar(self, username):
        client = Client()
        client.login(username=username, password="pass12345")
        return client.get(reverse("management:dashboard")).content.decode()

    def test_gestor_sidebar_hides_network_items(self):
        html = self._sidebar("gestor1")
        self.assertIn("Turmas", html)
        self.assertIn("Equipe", html)
        self.assertIn("Importar matrículas", html)
        self.assertNotIn("Painel municipal", html)
        self.assertNotIn(">Município<", html)
        self.assertNotIn("Anos letivos", html)
        self.assertNotIn("Comparar escolas", html)
        self.assertNotIn("Navegação em rede", html)
        self.assertNotIn(">Matriz<", html)
        self.assertNotIn("Instrumentos", html)

    def test_aee_sidebar_hides_cadastro_write(self):
        self._user("aee1", Role.Code.AEE, self.school_a)
        html = self._sidebar("aee1")
        self.assertIn("Estudantes", html)
        self.assertIn("Turmas", html)
        self.assertNotIn("Importar matrículas", html)
        self.assertNotIn("Equipe", html)
        self.assertNotIn("Painel municipal", html)
        self.assertNotIn("Matrículas", html)

    def test_secretaria_sidebar_keeps_network_items(self):
        self._user("sec1", Role.Code.SECRETARIA, self.school_a)
        html = self._sidebar("sec1")
        self.assertIn("Painel municipal", html)
        self.assertIn("Município", html)
        self.assertIn("Anos letivos", html)
        self.assertIn("Matriz", html)
        self.assertIn("Comparar escolas", html)

    def test_professor_reports_hide_network_card(self):
        client = Client()
        client.login(username="prof1", password="pass12345")
        html = client.get(reverse("management:reports")).content.decode()
        self.assertIn("Relatórios", html)
        self.assertNotIn("Painel municipal", html)
        self.assertNotIn("Rede municipal", html)
        self.assertNotIn("Importar matrículas", html)
        self.assertIn("Minhas turmas", html)

    def test_missing_role_does_not_empty_sidebar(self):
        from apps.core.permissions import nav_flags
        from apps.core.templatetags.nav_tags import nav_on

        user = self._user("norole", Role.Code.GESTOR, self.school_a)
        user.userprofile.role = None
        user.userprofile.save()
        flags = nav_flags(user)
        self.assertTrue(flags["section_gestao"])
        self.assertTrue(flags["schools"])
        self.assertTrue(nav_on({}, "section_gestao"))
        self.assertTrue(nav_on({"ready": False}, "section_gestao"))
        self.assertTrue(nav_on({"ready": True}, "section_gestao"))
        self.assertFalse(nav_on({"ready": True, "section_gestao": False, "dashboard": False}, "section_gestao"))

    def test_gestor_topbar_shows_role_and_menu(self):
        html = self._sidebar("gestor1")
        self.assertIn("Gestor", html)
        self.assertIn("Dashboard", html)
        self.assertIn("Sala de aula", html)


class CsrfProductionTests(TestCase):
    def test_csrf_origins_include_www(self):
        from config.settings.base import csrf_origins_from_hosts

        origins = csrf_origins_from_hosts(["edu.innomove.com.br"])
        self.assertIn("https://edu.innomove.com.br", origins)
        self.assertIn("https://www.edu.innomove.com.br", origins)

    def test_cpanel_https_header(self):
        from django.http import HttpResponse
        from django.test import RequestFactory

        from apps.core.middleware import CpanelHttpsMiddleware

        factory = RequestFactory()
        request = factory.get("/login/")
        request.META["HTTPS"] = "on"
        captured = {}

        def inner(req):
            captured["proto"] = req.META.get("HTTP_X_FORWARDED_PROTO")
            return HttpResponse("ok")

        CpanelHttpsMiddleware(inner)(request)
        self.assertEqual(captured["proto"], "https")

    def test_csrf_failure_page(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("login"), {"username": "x", "password": "y"})
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Sessão expirada", status_code=403)


class CadastroCrudTests(BaseFixtureTestCase):
    def test_gestor_cannot_create_school(self):
        client = Client()
        client.login(username="gestor1", password="pass12345")
        self.assertEqual(client.get(reverse("management:school_create")).status_code, 403)
        client.post(
            reverse("management:school_create"),
            {"name": "Hack", "code": "HX1", "municipality": self.municipality.pk, "address": ""},
        )
        self.assertFalse(School.objects.filter(code="HX1").exists())

    def test_secretaria_can_create_school(self):
        self._user("sec1", Role.Code.SECRETARIA, self.school_a)
        client = Client()
        client.login(username="sec1", password="pass12345")
        response = client.post(
            reverse("management:school_create"),
            {"name": "Nova Escola", "code": "N1", "municipality": self.municipality.pk, "address": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(School.objects.filter(code="N1").exists())

    def test_gestor_can_create_classroom_in_own_school(self):
        client = Client()
        client.login(username="gestor1", password="pass12345")
        response = client.post(
            reverse("management:classroom_create"),
            {
                "school": self.school_a.pk,
                "school_year": self.year.pk,
                "name": "Infantil V C",
                "grade_label": "Infantil V",
                "shift": "Manhã",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Classroom.objects.filter(name="Infantil V C", school=self.school_a).exists())

    def test_gestor_cannot_create_classroom_in_other_school(self):
        client = Client()
        client.login(username="gestor1", password="pass12345")
        client.post(
            reverse("management:classroom_create"),
            {
                "school": self.school_b.pk,
                "school_year": self.year.pk,
                "name": "Hack Turma",
                "grade_label": "1º Ano",
                "shift": "",
            },
        )
        self.assertFalse(Classroom.objects.filter(name="Hack Turma", school=self.school_b).exists())

    def test_gestor_can_archive_own_classroom(self):
        client = Client()
        client.login(username="gestor1", password="pass12345")
        response = client.post(reverse("management:classroom_archive", args=[self.classroom_a.pk]))
        self.assertEqual(response.status_code, 302)
        self.classroom_a.refresh_from_db()
        self.assertFalse(self.classroom_a.is_active)

    def test_professor_cannot_open_cadastro_write(self):
        client = Client()
        client.login(username="prof1", password="pass12345")
        self.assertEqual(client.get(reverse("management:schools")).status_code, 403)
        self.assertEqual(client.get(reverse("management:classroom_create")).status_code, 403)


class OperationalFeedTests(BaseFixtureTestCase):
    def test_secretaria_can_create_municipality_matrix_and_instrument(self):
        self._user("sec1", Role.Code.SECRETARIA, self.school_a)
        client = Client()
        client.login(username="sec1", password="pass12345")
        self.assertEqual(client.get(reverse("management:municipality_create")).status_code, 200)
        response = client.post(
            reverse("management:municipality_create"),
            {"name": "Garanhuns", "state": "PE", "slug": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Municipality.objects.filter(slug="garanhuns").exists())

        response = client.post(reverse("management:matrix_create"), {"name": "Matriz Rede", "description": "", "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        matrix = PedagogicalMatrix.objects.get(name="Matriz Rede")
        response = client.post(
            reverse("management:matrix_version_create"),
            {"matrix": matrix.pk, "version_label": "2026", "framework_reference": "Currículo PE", "notes": ""},
        )
        self.assertEqual(response.status_code, 302)
        version = MatrixVersion.objects.get(matrix=matrix, version_label="2026")
        self.assertTrue(version.status_labels.exists())

        response = client.post(
            reverse("management:dimension_create"),
            {"matrix_version": version.pk, "code": "oral", "name": "Oralidade", "practice_axis": "Oralidade", "description": "", "order": 1},
        )
        self.assertEqual(response.status_code, 302)
        dimension = DevelopmentDimension.objects.get(code="oral", matrix_version=version)
        response = client.post(
            reverse("management:skill_create"),
            {
                "dimension": dimension.pk,
                "code": "oral_01",
                "bncc_code": "EF01LP01PE",
                "name": "Escutar com atenção",
                "knowledge_object": "Escuta",
                "description": "",
                "curriculum_notes": "",
                "order": 1,
            },
        )
        self.assertEqual(response.status_code, 302)
        skill = Skill.objects.get(code="oral_01")
        response = client.post(
            reverse("management:instrument_create"),
            {
                "matrix_version": version.pk,
                "skill": skill.pk,
                "title": "Sondagem escuta",
                "description": "",
                "instrument_type": AssessmentInstrument.InstrumentType.DIGITAL,
                "estimated_minutes": 12,
                "is_published": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        instrument = AssessmentInstrument.objects.get(title="Sondagem escuta")
        response = client.post(
            reverse("management:instrument_items", args=[instrument.pk]),
            {"prompt": "A criança escuta a parlenda?", "item_type": AssessmentItem.ItemType.SINGLE_SELECT, "options_text": "Sim|*\nNão|0"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(instrument.items.count(), 1)
        self.assertTrue(instrument.scoring_rules.exists())

    def test_gestor_cannot_author_network_catalog(self):
        client = Client()
        client.login(username="gestor1", password="pass12345")
        self.assertEqual(client.get(reverse("management:municipality_create")).status_code, 403)
        self.assertEqual(client.get(reverse("management:matrix_create")).status_code, 403)
        self.assertEqual(client.get(reverse("management:instrument_create")).status_code, 403)

    def test_coordenador_can_create_intervention_template(self):
        self._user("coord1", Role.Code.COORDENADOR, self.school_a)
        client = Client()
        client.login(username="coord1", password="pass12345")
        response = client.post(
            reverse("management:intervention_template_create"),
            {
                "skill": self.skill.pk,
                "title": "Jogo de rimas em sala",
                "objective": "Fortalecer consciência de rimas",
                "suggested_activities": "Parlenda\nJogo oral",
                "suggested_duration_days": 14,
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(InterventionTemplate.objects.filter(title="Jogo de rimas em sala").exists())

    def test_secretaria_can_create_aee_staff(self):
        self._user("sec1", Role.Code.SECRETARIA, self.school_a)
        aee_role = Role.objects.get(code=Role.Code.AEE)
        client = Client()
        client.login(username="sec1", password="pass12345")
        response = client.post(
            reverse("management:teacher_create"),
            {
                "first_name": "Ana",
                "last_name": "AEE",
                "username": "aee.ana",
                "email": "aee@example.com",
                "password": "pass12345",
                "role": aee_role.pk,
                "school": self.school_a.pk,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="aee.ana")
        self.assertEqual(user.role_code, Role.Code.AEE)
        self.assertEqual(user.profile.school_id, self.school_a.pk)

    def test_aee_can_create_support_plan_professor_cannot(self):
        aee = self._user("aee1", Role.Code.AEE, self.school_a)
        client = Client()
        client.login(username="prof1", password="pass12345")
        self.assertEqual(client.get(reverse("teacher:support_plan_create", args=[self.student.pk])).status_code, 403)

        client.login(username="aee1", password="pass12345")
        response = client.post(
            reverse("teacher:support_plan_create", args=[self.student.pk]),
            {
                "school_year": self.year.pk,
                "status": StudentSupportPlan.Status.ACTIVE,
                "start_date": "2026-02-01",
                "end_date": "",
                "notes": "Tempo ampliado e instruções curtas.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StudentSupportPlan.objects.filter(student=self.student, created_by=aee).exists())

    def test_professor_can_update_intervention_status(self):
        intervention = StudentIntervention.objects.create(
            enrollment=self.enrollment,
            student=self.student,
            skill=self.skill,
            responsible=self.professor,
            objective="Trabalhar rimas",
            status=InterventionStatus.PLANNED,
        )
        client = Client()
        client.login(username="prof1", password="pass12345")
        response = client.post(
            reverse("teacher:intervention_status", args=[intervention.pk]),
            {"status": InterventionStatus.IN_PROGRESS},
        )
        self.assertEqual(response.status_code, 302)
        intervention.refresh_from_db()
        self.assertEqual(intervention.status, InterventionStatus.IN_PROGRESS)


class LongitudinalTests(BaseFixtureTestCase):
    def test_new_enrollment_keeps_history(self):
        old_id = self.enrollment.pk
        new_enrollment = enroll_student_in_new_year(student=self.student, classroom=self.classroom_next)
        self.assertNotEqual(old_id, new_enrollment.pk)
        self.assertTrue(Enrollment.objects.filter(pk=old_id).exists())
        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 2)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.classroom_id, self.classroom_a.pk)

    def test_assessment_stays_on_enrollment(self):
        session = start_session(enrollment=self.enrollment, instrument=self.instrument, started_by=self.professor)
        enroll_student_in_new_year(student=self.student, classroom=self.classroom_next)
        session.refresh_from_db()
        self.assertEqual(session.enrollment_id, self.enrollment.pk)
        self.assertEqual(session.enrollment.classroom_id, self.classroom_a.pk)


class MatrixVersionFreezeTests(BaseFixtureTestCase):
    def test_matrix_change_does_not_alter_past_session(self):
        session = start_session(enrollment=self.enrollment, instrument=self.instrument, started_by=self.professor)
        frozen = session.matrix_version_id
        self.instrument.matrix_version = self.version2
        self.instrument.save()
        session.refresh_from_db()
        self.assertEqual(session.matrix_version_id, frozen)


class ScoringAndRecommendationTests(BaseFixtureTestCase):
    def test_skill_status_calculation(self):
        session = start_session(enrollment=self.enrollment, instrument=self.instrument, started_by=self.professor)
        save_response(session=session, item=self.item, option=self.opt_ok)
        complete_session(session)
        result = session.skill_results.get()
        self.assertEqual(result.status_code, "demonstrated")

    def test_intervention_recommendation(self):
        template = recommend_template_for_result(skill=self.skill, status_code="needs_support")
        self.assertIsNotNone(template)
        self.assertEqual(template.skill_id, self.skill.pk)


class ImportTests(BaseFixtureTestCase):
    def test_import_students_creates_enrollment_without_duplicating(self):
        csv_data = (
            "matricula,nome,data_nascimento,escola,turma,ano_letivo\n"
            "T001,Criança Teste Atualizada,01/05/2020,A1,Infantil V A,2026\n"
            "T002,Nova Criança,02/06/2020,A1,Infantil V A,2026\n"
        ).encode("utf-8")
        job = import_students_csv(file_obj=BytesIO(csv_data), school_year=self.year, created_by=self.gestor)
        self.assertEqual(job.success_count, 2)
        self.assertEqual(Student.objects.filter(external_code="T001").count(), 1)
        self.student.refresh_from_db()
        self.assertEqual(self.student.full_name, "Criança Teste Atualizada")
        self.assertTrue(Student.objects.filter(external_code="T002").exists())
