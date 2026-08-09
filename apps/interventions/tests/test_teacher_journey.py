"""Domain, portal and API tests for the teacher operational journey."""
from datetime import date, timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.accessibility.models import AccessibilityFeature
from apps.accessibility.services.catalog import ensure_default_features
from apps.accessibility.services.profile import set_student_features
from apps.analytics.models import StudentSkillStatus
from apps.core.models import AuditLog
from apps.core.tests.test_critical import BaseFixtureTestCase
from apps.curriculum.models import DevelopmentDimension, Skill
from apps.evidences.models import Evidence
from apps.interventions.models import (
    ClassroomIntervention,
    FollowupResult,
    InterventionStatus,
    InterventionTemplate,
    StudentIntervention,
)
from apps.interventions.services.apply_group import apply_suggested_group
from apps.interventions.services.grouping import suggest_groups
from apps.interventions.services.quick_followup import record_batch_followup
from apps.interventions.services.reassessment import suggestions_for_snapshot
from apps.interventions.services.snapshot import load_classroom_snapshot
from apps.interventions.services.teacher_actions import build_teacher_action_queue
from apps.planning.models import PedagogicalPlan
from apps.planning.services.lesson_builder import accept_lesson_proposal, build_lesson_proposal
from apps.schools.services.school_year import enroll_student_in_new_year
from apps.students.models import Enrollment, FamilyLink, Student


class TeacherJourneyFixture(BaseFixtureTestCase):
    def setUp(self):
        super().setUp()
        dim_seg = DevelopmentDimension.objects.create(
            matrix_version=self.version, code="segmentacao", name="Segmentação silábica"
        )
        self.skill_seg = Skill.objects.create(dimension=dim_seg, code="seg_base", name="Segmentar oralmente palavras")
        self.template_rimas = InterventionTemplate.objects.get(skill=self.skill)
        self.template_rimas.title = "Jogo das Rimas"
        self.template_rimas.suggested_activity_minutes = 10
        self.template_rimas.save()
        self.template_seg = InterventionTemplate.objects.create(
            skill=self.skill_seg,
            title="Palmas nas Sílabas",
            objective="Segmentar com palmas",
            suggested_activities="Palmas nas sílabas\nNomes da turma",
            suggested_activity_minutes=15,
        )
        self.familia = self._user("familia1", Role.Code.FAMILIA, self.school_a)
        FamilyLink.objects.create(user=self.familia, student=self.student)
        self.extra_students = []
        for i, name in enumerate(["Theo Martins", "Laura Mendes", "Noah Barbosa", "Valentina Costa"], start=2):
            student = Student.objects.create(full_name=name, external_code=f"T00{i}", birth_date=date(2020, 6, i))
            Enrollment.objects.create(student=student, classroom=self.classroom_a, school_year=self.year)
            self.extra_students.append(student)
        self.pending_student = Student.objects.create(full_name="Arthur Lima", external_code="T009", birth_date=date(2020, 8, 1))
        Enrollment.objects.create(student=self.pending_student, classroom=self.classroom_a, school_year=self.year)
        self.other_student = Student.objects.create(full_name="Alice Outra Turma", external_code="B001", birth_date=date(2020, 3, 1))
        Enrollment.objects.create(student=self.other_student, classroom=self.classroom_b, school_year=self.year)
        features = ensure_default_features()
        set_student_features(
            student=self.extra_students[0],
            feature_codes=[AccessibilityFeature.Code.MOTOR_NO_DRAG],
            actor=self.gestor,
        )
        self._mark_attention(self.student, self.skill)
        for extra in self.extra_students:
            self._mark_attention(extra, self.skill)
        for extra in self.extra_students[:3]:
            self._mark_attention(extra, self.skill_seg)

    def _mark_attention(self, student, skill, status_code="needs_support"):
        enrollment = student.current_enrollment()
        StudentSkillStatus.objects.update_or_create(
            student=student,
            skill=skill,
            defaults={
                "enrollment": enrollment,
                "status_code": status_code,
                "status_label": "Necessita maior mediação",
                "needs_attention": True,
                "raw_score": 1,
                "max_score": 5,
            },
        )


class TeacherActionQueueTests(TeacherJourneyFixture):
    def test_professor_only_sees_own_classroom_actions(self):
        self._mark_attention(self.other_student, self.skill)
        queue = build_teacher_action_queue(self.professor)
        classroom_ids = {a.classroom_id for a in queue.actions}
        self.assertIn(self.classroom_a.pk, classroom_ids)
        self.assertNotIn(self.classroom_b.pk, classroom_ids)

    def test_pending_assessment_appears(self):
        queue = build_teacher_action_queue(self.professor)
        types = [a.type for a in queue.actions]
        self.assertIn("ASSESSMENT_PENDING", types)
        pending = next(a for a in queue.actions if a.type == "ASSESSMENT_PENDING")
        self.assertIn(self.pending_student.pk, pending.student_ids)

    def test_common_need_creates_group_action(self):
        queue = build_teacher_action_queue(self.professor)
        group = next(a for a in queue.actions if a.type == "SKILL_GROUP_INTERVENTION" and a.skill_id == self.skill.pk)
        self.assertGreaterEqual(group.count, 4)
        self.assertIn(self.student.pk, group.student_ids)
        self.assertFalse(group.title.startswith(str(group.count)))


class GroupingTests(TeacherJourneyFixture):
    def test_groups_by_skill_and_active_enrollments(self):
        snapshot = load_classroom_snapshot(self.classroom_a)
        groups = suggest_groups(snapshot)
        rimas = next(g for g in groups if g.skill_id == self.skill.pk)
        self.assertGreaterEqual(rimas.size, 4)
        self.assertTrue(all(sid != self.other_student.pk for sid in rimas.student_ids))
        seg = next(g for g in groups if g.skill_id == self.skill_seg.pk)
        self.assertGreaterEqual(seg.size, 2)

    def test_accessibility_notes_for_no_drag(self):
        snapshot = load_classroom_snapshot(self.classroom_a)
        rimas = next(g for g in suggest_groups(snapshot) if g.skill_id == self.skill.pk)
        joined = " ".join(rimas.accessibility_notes).lower()
        self.assertIn("theo", joined)
        self.assertTrue("arrastar" in joined or "alternativa" in joined)

    def test_professor_cannot_include_other_classroom_student(self):
        snapshot = load_classroom_snapshot(self.classroom_a)
        from apps.interventions.services.grouping import suggest_group_for_skill

        group = suggest_group_for_skill(
            snapshot,
            self.skill.pk,
            student_ids=[self.student.pk, self.other_student.pk],
        )
        self.assertIsNotNone(group)
        self.assertNotIn(self.other_student.pk, group.student_ids)


class ApplyAndFollowupTests(TeacherJourneyFixture):
    def test_apply_group_creates_structure_and_is_idempotent(self):
        result = apply_suggested_group(
            user=self.professor,
            classroom=self.classroom_a,
            skill=self.skill,
            student_ids=[self.student.pk] + [s.pk for s in self.extra_students],
            template=self.template_rimas,
        )
        self.assertTrue(result.created)
        self.assertEqual(result.classroom_intervention.template_id, self.template_rimas.pk)
        self.assertTrue(result.plan.pk)
        self.assertGreaterEqual(len(result.student_interventions), 4)
        again = apply_suggested_group(
            user=self.professor,
            classroom=self.classroom_a,
            skill=self.skill,
            student_ids=[self.student.pk] + [s.pk for s in self.extra_students],
            template=self.template_rimas,
        )
        self.assertFalse(again.created)
        self.assertEqual(result.classroom_intervention.pk, again.classroom_intervention.pk)
        self.assertEqual(
            ClassroomIntervention.objects.filter(classroom=self.classroom_a, skill=self.skill, starts_on=date.today()).count(),
            1,
        )

    def test_quick_followup_does_not_become_formal_assessment(self):
        applied = apply_suggested_group(
            user=self.professor,
            classroom=self.classroom_a,
            skill=self.skill,
            student_ids=[self.student.pk, self.extra_students[0].pk],
            template=self.template_rimas,
        )
        before_status = StudentSkillStatus.objects.get(student=self.student, skill=self.skill)
        results = {
            applied.student_interventions[0].pk: FollowupResult.PROGRESSED,
            applied.student_interventions[1].pk: FollowupResult.NOT_OBSERVED,
        }
        batch = record_batch_followup(
            user=self.professor,
            interventions=applied.student_interventions,
            results=results,
            classroom_intervention=applied.classroom_intervention,
        )
        self.assertEqual(len(batch.entries), 2)
        after_status = StudentSkillStatus.objects.get(student=self.student, skill=self.skill)
        self.assertEqual(before_status.status_code, after_status.status_code)
        self.assertTrue(after_status.needs_attention)
        not_observed = next(e for e in batch.entries if e.result == FollowupResult.NOT_OBSERVED)
        self.assertIn("não foi possível observar", not_observed.evidence.description.lower())
        self.assertTrue(AuditLog.objects.filter(object_type="StudentIntervention", actor=self.professor).exists())
        # double post does not duplicate evidence
        record_batch_followup(
            user=self.professor,
            interventions=applied.student_interventions,
            results=results,
            classroom_intervention=applied.classroom_intervention,
        )
        self.assertEqual(
            Evidence.objects.filter(student=self.student, skill=self.skill, file_type=Evidence.FileType.TEXT).count(),
            1,
        )


class ReassessmentTests(TeacherJourneyFixture):
    def test_reassessment_appears_after_configured_days_and_not_auto_session(self):
        past = timezone.now() - timedelta(days=10)
        iv = StudentIntervention.objects.create(
            enrollment=self.enrollment,
            student=self.student,
            skill=self.skill,
            template=self.template_rimas,
            responsible=self.professor,
            objective="Jogo das Rimas",
            status=InterventionStatus.COMPLETED,
            followup_result=FollowupResult.PROGRESSED,
            followup_recorded_at=past,
            starts_on=date.today() - timedelta(days=14),
        )
        StudentIntervention.objects.filter(pk=iv.pk).update(created_at=past, updated_at=past, followup_recorded_at=past)
        snapshot = load_classroom_snapshot(self.classroom_a)
        suggestions = suggestions_for_snapshot(snapshot)
        self.assertTrue(any(s.student_id == self.student.pk and s.skill_id == self.skill.pk for s in suggestions))
        from apps.assessments.models import AssessmentSession

        self.assertFalse(AssessmentSession.objects.filter(enrollment=self.enrollment).exists())

    def test_new_session_clears_reassessment(self):
        past = timezone.now() - timedelta(days=10)
        iv = StudentIntervention.objects.create(
            enrollment=self.enrollment,
            student=self.student,
            skill=self.skill,
            responsible=self.professor,
            objective="Jogo",
            status=InterventionStatus.COMPLETED,
            followup_result=FollowupResult.PROGRESSED,
            followup_recorded_at=past,
        )
        StudentIntervention.objects.filter(pk=iv.pk).update(followup_recorded_at=past, updated_at=past)
        from apps.assessments.services import complete_session, save_response, start_session

        session = start_session(enrollment=self.enrollment, instrument=self.instrument, started_by=self.professor)
        save_response(session=session, item=self.item, option=self.opt_ok)
        complete_session(session)
        snapshot = load_classroom_snapshot(self.classroom_a)
        suggestions = suggestions_for_snapshot(snapshot)
        self.assertFalse(any(s.student_id == self.student.pk and s.skill_id == self.skill.pk for s in suggestions))


class LessonBuilderTests(TeacherJourneyFixture):
    def test_builds_45_minute_plan_from_needs(self):
        snapshot = load_classroom_snapshot(self.classroom_a)
        proposal = build_lesson_proposal(snapshot, duration_minutes=45)
        self.assertEqual(proposal.duration_minutes, 45)
        self.assertTrue(any(b.kind == "welcome" for b in proposal.blocks))
        self.assertTrue(any(b.kind == "closing" for b in proposal.blocks))
        self.assertTrue(any(b.skill_id == self.skill.pk for b in proposal.blocks if b.kind == "group"))
        plan = accept_lesson_proposal(user=self.professor, snapshot=snapshot, proposal=proposal)
        self.assertTrue(plan.activities.exists())
        self.assertEqual(plan.duration_minutes, 45)


class TeacherPortalRBACTests(TeacherJourneyFixture):
    def test_hoje_page_loads_for_teacher(self):
        client = Client()
        client.login(username="prof1", password="pass12345")
        response = client.get(reverse("teacher:today"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hoje")
        self.assertContains(response, "Iniciar")
        self.assertNotContains(response, "5 crianças")
        self.assertNotContains(response, "Planejar minha aula")

    def test_pending_assessments_and_group_open_play(self):
        client = Client()
        client.login(username="prof1", password="pass12345")
        pending = client.get(reverse("teacher:pending_assessments", args=[self.classroom_a.pk]))
        self.assertEqual(pending.status_code, 200)
        self.assertContains(pending, "Arthur Lima")
        self.assertContains(pending, "Iniciar sondagem")
        group = client.get(reverse("teacher:suggested_group", args=[self.classroom_a.pk, self.skill.pk]))
        self.assertEqual(group.status_code, 200)
        self.assertContains(group, "Iniciar sondagem")
        self.assertContains(group, reverse("assessment:preview", args=[self.enrollment.pk, self.instrument.pk]))

    def test_teacher_cannot_open_other_classroom_group(self):
        client = Client()
        client.login(username="prof1", password="pass12345")
        response = client.get(reverse("teacher:suggested_group", args=[self.classroom_b.pk, self.skill.pk]))
        self.assertEqual(response.status_code, 302)

    def test_apply_and_followup_flow(self):
        client = Client()
        client.login(username="prof1", password="pass12345")
        response = client.post(
            reverse("teacher:suggested_group", args=[self.classroom_a.pk, self.skill.pk]),
            {"student_ids": [self.student.pk] + [s.pk for s in self.extra_students]},
        )
        self.assertEqual(response.status_code, 302)
        ci = ClassroomIntervention.objects.get(classroom=self.classroom_a, skill=self.skill)
        follow = client.get(reverse("teacher:quick_followup", args=[ci.pk]))
        self.assertEqual(follow.status_code, 200)
        self.assertContains(follow, "Avançou")
        payload = {"general_notes": "Turma envolvida."}
        for iv in ci.student_links.all():
            payload[f"result_{iv.pk}"] = FollowupResult.PROGRESSED
        saved = client.post(reverse("teacher:quick_followup", args=[ci.pk]), payload)
        self.assertEqual(saved.status_code, 302)
        self.assertTrue(ci.student_links.filter(followup_result=FollowupResult.PROGRESSED).exists())

    def test_family_cannot_access_teacher_hoje(self):
        client = Client()
        client.login(username="familia1", password="pass12345")
        response = client.get(reverse("teacher:today"))
        self.assertIn(response.status_code, (302, 403))

    def test_anonymous_is_redirected(self):
        client = Client()
        response = client.get(reverse("teacher:today"))
        self.assertEqual(response.status_code, 302)


class TeacherAPITests(TeacherJourneyFixture):
    def test_teacher_a_cannot_read_teacher_b_classroom(self):
        client = APIClient()
        client.login(username="prof1", password="pass12345")
        response = client.get(reverse("api_teacher_classroom_summary", args=[self.classroom_b.pk]))
        self.assertEqual(response.status_code, 403)

    def test_teacher_a_cannot_write_teacher_b_intervention(self):
        ci = ClassroomIntervention.objects.create(
            classroom=self.classroom_b,
            skill=self.skill,
            responsible=self.professor_other,
            objective="Outra turma",
            status=InterventionStatus.IN_PROGRESS,
        )
        client = APIClient()
        client.login(username="prof1", password="pass12345")
        response = client.post(
            reverse("api_teacher_batch_followup", args=[ci.pk]),
            {"results": {"1": FollowupResult.PROGRESSED}},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_today_api_scoped_and_family_blocked(self):
        client = APIClient()
        client.login(username="prof1", password="pass12345")
        response = client.get(reverse("api_teacher_today"))
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.data["classrooms"]}
        self.assertIn(self.classroom_a.pk, ids)
        self.assertNotIn(self.classroom_b.pk, ids)
        family = APIClient()
        family.login(username="familia1", password="pass12345")
        forbidden = family.get(reverse("api_teacher_today"))
        self.assertEqual(forbidden.status_code, 403)

    def test_anonymous_api(self):
        client = APIClient()
        response = client.get(reverse("api_teacher_today"))
        self.assertIn(response.status_code, (401, 403))

    def test_app_login_rejects_aee_gestao_and_familia(self):
        self._user("aee1", Role.Code.AEE, self.school_a)
        client = APIClient()
        for username in ("aee1", "gestor1", "familia1"):
            denied = client.post(
                reverse("api_teacher_login"),
                {"username": username, "password": "pass12345"},
                format="json",
            )
            self.assertEqual(denied.status_code, 403, username)
            self.assertIn("só para a professora", denied.data["detail"])

        session = APIClient()
        session.login(username="aee1", password="pass12345")
        bootstrap = session.get(reverse("api_teacher_bootstrap"))
        self.assertEqual(bootstrap.status_code, 403)

    def test_app_login_bootstrap_and_ludic(self):
        client = APIClient()
        denied = client.post(reverse("api_teacher_login"), {"username": "familia1", "password": "pass12345"}, format="json")
        self.assertEqual(denied.status_code, 403)
        bad = client.post(reverse("api_teacher_login"), {"username": "prof1", "password": "wrong"}, format="json")
        self.assertEqual(bad.status_code, 400)
        login = client.post(reverse("api_teacher_login"), {"username": "prof1", "password": "pass12345"}, format="json")
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.data["token"])
        self.assertEqual(login.data["teacher"]["username"], "prof1")
        classroom_ids = {item["id"] for item in login.data["classrooms"]}
        self.assertIn(self.classroom_a.pk, classroom_ids)
        self.assertNotIn(self.classroom_b.pk, classroom_ids)
        room = next(c for c in login.data["classrooms"] if c["id"] == self.classroom_a.pk)
        self.assertTrue(any(s["full_name"] == "Criança Teste" for s in room["students"]))

        client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")
        bootstrap = client.get(reverse("api_teacher_bootstrap"))
        self.assertEqual(bootstrap.status_code, 200)
        self.assertEqual(len(bootstrap.data["classrooms"]), len(login.data["classrooms"]))

        ludic = client.post(
            reverse("api_teacher_ludic"),
            {
                "student_id": self.student.pk,
                "enrollment_id": self.enrollment.pk,
                "activity_id": "rimas",
                "activity_title": "Jogo das rimas",
                "skill_code": self.skill.code,
                "mode": "survey",
                "label": "Habilidade demonstrada",
                "score": 1,
                "total": 1,
                "needs_attention": False,
                "answers": [{"correct": True, "score": 1}],
            },
            format="json",
        )
        self.assertEqual(ludic.status_code, 201)
        self.assertTrue(ludic.data["session_id"])
        self.assertTrue(Evidence.objects.filter(student=self.student, recorded_by=self.professor).exists())
        self.assertTrue(StudentSkillStatus.objects.filter(student=self.student, skill=self.skill).exists())


class LongitudinalJourneyTests(TeacherJourneyFixture):
    def test_new_year_keeps_followup_history(self):
        applied = apply_suggested_group(
            user=self.professor,
            classroom=self.classroom_a,
            skill=self.skill,
            student_ids=[self.student.pk],
            template=self.template_rimas,
        )
        record_batch_followup(
            user=self.professor,
            interventions=applied.student_interventions,
            results={applied.student_interventions[0].pk: FollowupResult.PROGRESSED},
            classroom_intervention=applied.classroom_intervention,
        )
        evidence_id = Evidence.objects.get(student=self.student, skill=self.skill).pk
        enroll_student_in_new_year(student=self.student, classroom=self.classroom_next)
        self.assertTrue(Evidence.objects.filter(pk=evidence_id).exists())
        self.assertTrue(StudentIntervention.objects.filter(student=self.student, skill=self.skill).exists())
        self.assertTrue(StudentSkillStatus.objects.filter(student=self.student, skill=self.skill).exists())
