"""Mandatory accessibility / inclusive assessment tests."""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accessibility.models import StudentAccessibilityProfile
from apps.accessibility.permissions import can_change_accessibility_profile
from apps.accessibility.services.catalog import ensure_default_features
from apps.accessibility.services.profile import set_student_features
from apps.accounts.models import Role, UserProfile
from apps.analytics.services.accessibility_indicators import network_accessibility_stats
from apps.assessments.models import (
    AssessmentInstrument,
    AssessmentItem,
    AssessmentItemVariant,
    AssessmentOption,
    AssessmentResponse,
    AssessmentSession,
    ItemAccessRequirement,
    ScoringRule,
)
from apps.assessments.services import AccessibilityAssessmentResolver, complete_session, save_response, start_session
from apps.assessments.services.scoring import score_session
from apps.curriculum.models import DevelopmentDimension, MatrixVersion, PedagogicalMatrix, Skill, StatusLabelConfig
from apps.schools.models import Classroom, Municipality, School, SchoolYear, TeacherClassroom
from apps.students.models import Enrollment, Student

User = get_user_model()


class AccessibilityFixtureTestCase(TestCase):
    def setUp(self):
        for code, name in Role.Code.choices:
            Role.objects.get_or_create(code=code, defaults={"name": name})
        self.features = ensure_default_features()
        self.municipality = Municipality.objects.create(name="Jucati", slug="jucati-a11y", state="PE")
        self.year = SchoolYear.objects.create(year=2026, label="2026", is_active=True)
        self.school_a = School.objects.create(municipality=self.municipality, name="Escola A", code="A11Y-A")
        self.school_b = School.objects.create(municipality=self.municipality, name="Escola B", code="A11Y-B")
        self.classroom_a = Classroom.objects.create(
            school=self.school_a, school_year=self.year, name="Turma A", grade_label="Infantil V"
        )
        self.classroom_b = Classroom.objects.create(
            school=self.school_b, school_year=self.year, name="Turma B", grade_label="Infantil V"
        )
        self.professor = self._user("prof_a11y", Role.Code.PROFESSOR, self.school_a)
        self.professor_b = self._user("prof_b11y", Role.Code.PROFESSOR, self.school_b)
        self.aee = self._user("aee_a11y", Role.Code.AEE, self.school_a)
        self.coordenador = self._user("coord_a11y", Role.Code.COORDENADOR, self.school_a)
        TeacherClassroom.objects.create(teacher=self.professor, classroom=self.classroom_a)
        TeacherClassroom.objects.create(teacher=self.professor_b, classroom=self.classroom_b)

        self.student = Student.objects.create(full_name="Estudante A11y", external_code="A11Y001", birth_date=date(2020, 1, 1))
        self.enrollment = Enrollment.objects.create(
            student=self.student, classroom=self.classroom_a, school_year=self.year
        )

        matrix = PedagogicalMatrix.objects.create(name="Matriz A11y")
        self.version = MatrixVersion.objects.create(
            matrix=matrix, version_label="v1", is_published=True, published_at=timezone.now()
        )
        dim = DevelopmentDimension.objects.create(matrix_version=self.version, code="rimas", name="Rimas")
        self.skill = Skill.objects.create(dimension=dim, code="rimas_a11y", name="Reconhecer rimas")
        for code, label in [
            ("demonstrated", "Habilidade demonstrada"),
            ("needs_support", "Necessita maior mediação"),
            ("developing", "Em desenvolvimento"),
            ("not_observed", "Não observado"),
        ]:
            StatusLabelConfig.objects.create(matrix_version=self.version, code=code, label=label)

        self.instrument = AssessmentInstrument.objects.create(
            matrix_version=self.version,
            skill=self.skill,
            title="Sondagem A11y",
            instrument_type=AssessmentInstrument.InstrumentType.DIGITAL,
        )
        self.item_ok = AssessmentItem.objects.create(
            instrument=self.instrument,
            order=1,
            item_type=AssessmentItem.ItemType.SINGLE_SELECT,
            prompt="Qual rima com SOL?",
            code="RIM-A01",
        )
        ItemAccessRequirement.objects.create(
            item=self.item_ok,
            code=ItemAccessRequirement.RequirementCode.SUPPORTS_SCREEN_READER,
            is_required=False,
        )
        self.opt_ok = AssessmentOption.objects.create(
            item=self.item_ok, label="GOL", score_value=1, is_correct=True, order=1
        )
        AssessmentOption.objects.create(item=self.item_ok, label="MESA", score_value=0, is_correct=False, order=2)

        self.item_visual_drag = AssessmentItem.objects.create(
            instrument=self.instrument,
            order=2,
            item_type=AssessmentItem.ItemType.IMAGE_SELECT,
            prompt="Arraste a palavra que rima.",
            code="RIM-A02",
        )
        ItemAccessRequirement.objects.create(
            item=self.item_visual_drag,
            code=ItemAccessRequirement.RequirementCode.REQUIRES_VISION,
            is_required=True,
        )
        ItemAccessRequirement.objects.create(
            item=self.item_visual_drag,
            code=ItemAccessRequirement.RequirementCode.REQUIRES_DRAG,
            is_required=True,
        )
        self.opt_drag = AssessmentOption.objects.create(
            item=self.item_visual_drag, label="GOL", score_value=1, is_correct=True, order=1
        )
        AssessmentOption.objects.create(
            item=self.item_visual_drag, label="CASA", score_value=0, is_correct=False, order=2
        )

        self.variant_eq = AssessmentItemVariant.objects.create(
            parent_item=self.item_visual_drag,
            name="NoDrag",
            version=1,
            instruction_text="Selecione a palavra que rima (sem arrastar).",
            item_type_override=AssessmentItem.ItemType.SELECT_THEN_MATCH,
            equivalence_status=AssessmentItemVariant.EquivalenceStatus.EQUIVALENT,
            adaptation_type=AssessmentItemVariant.AdaptationType.ACCESS_ACCOMMODATION,
            pedagogical_approval_status=AssessmentItemVariant.ApprovalStatus.PUBLISHED,
            active=True,
        )
        self.variant_eq.supported_features.add(self.features["MOTOR_NO_DRAG"])

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
            max_score=2,
            result_code="demonstrated",
            status_code="demonstrated",
            label="Habilidade demonstrada",
        )
        self.resolver = AccessibilityAssessmentResolver()

    def _user(self, username, role_code, school):
        user = User.objects.create_user(username=username, password="pass12345", first_name=username)
        profile = user.userprofile
        profile.role = Role.objects.get(code=role_code)
        profile.school = school
        profile.save()
        return user


class ResolverTests(AccessibilityFixtureTestCase):
    def test_screen_reader_does_not_get_exclusive_visual_without_variant(self):
        set_student_features(student=self.student, feature_codes=["VISUAL_SCREEN_READER"], actor=self.aee)
        # Remove equivalent support path: create exclusive visual item without variant
        exclusive = AssessmentItem.objects.create(
            instrument=self.instrument,
            order=9,
            item_type=AssessmentItem.ItemType.VISUAL_TF,
            prompt="",
            code="VIS-ONLY",
        )
        ItemAccessRequirement.objects.create(
            item=exclusive,
            code=ItemAccessRequirement.RequirementCode.REQUIRES_VISION,
            is_required=True,
        )
        resolved = self.resolver.resolve_item(student=self.student, assessment_item=exclusive)
        self.assertEqual(resolved.equivalence, AssessmentResponse.EquivalenceApplied.REQUIRES_ALTERNATIVE)
        self.assertFalse(resolved.counts_toward_score)

    def test_incompatible_item_finds_equivalent_variant(self):
        set_student_features(student=self.student, feature_codes=["MOTOR_NO_DRAG"], actor=self.aee)
        resolved = self.resolver.resolve_item(student=self.student, assessment_item=self.item_visual_drag)
        self.assertEqual(resolved.equivalence, AssessmentResponse.EquivalenceApplied.EQUIVALENT)
        self.assertIsNotNone(resolved.variant)
        self.assertEqual(resolved.variant.pk, self.variant_eq.pk)

    def test_missing_variant_is_not_pedagogical_error(self):
        set_student_features(student=self.student, feature_codes=["MOTOR_NO_DRAG"], actor=self.aee)
        self.variant_eq.active = False
        self.variant_eq.save()
        resolved = self.resolver.resolve_item(student=self.student, assessment_item=self.item_visual_drag)
        self.assertEqual(resolved.equivalence, AssessmentResponse.EquivalenceApplied.REQUIRES_ALTERNATIVE)
        self.assertFalse(resolved.counts_toward_score)

    def test_not_applicable_does_not_reduce_performance(self):
        session = start_session(enrollment=self.enrollment, instrument=self.instrument, started_by=self.professor)
        save_response(session=session, item=self.item_ok, option=self.opt_ok, applied_by=self.professor)
        save_response(
            session=session,
            item=self.item_visual_drag,
            mark_not_applicable=True,
            applied_by=self.professor,
        )
        complete_session(session)
        result = session.skill_results.get()
        self.assertEqual(result.raw_score, 1)
        self.assertEqual(result.max_score, 1)
        self.assertNotEqual(result.status_code, "needs_support")

    def test_no_drag_uses_compatible_alternative(self):
        set_student_features(student=self.student, feature_codes=["MOTOR_NO_DRAG"], actor=self.aee)
        resolved = self.resolver.resolve_item(student=self.student, assessment_item=self.item_visual_drag)
        self.assertEqual(resolved.item_type, AssessmentItem.ItemType.SELECT_THEN_MATCH)

    def test_extra_time_does_not_reduce_score(self):
        set_student_features(student=self.student, feature_codes=["COGNITIVE_EXTRA_TIME"], actor=self.aee)
        session = start_session(enrollment=self.enrollment, instrument=self.instrument, started_by=self.professor)
        save_response(
            session=session,
            item=self.item_ok,
            option=self.opt_ok,
            applied_by=self.professor,
            response_time_seconds=9999,
        )
        save_response(
            session=session,
            item=self.item_visual_drag,
            option=self.opt_drag,
            applied_by=self.professor,
            response_time_seconds=9999,
        )
        complete_session(session)
        self.assertEqual(session.skill_results.get().raw_score, 2)

    def test_repeat_instruction_does_not_reduce_score(self):
        session = start_session(enrollment=self.enrollment, instrument=self.instrument, started_by=self.professor)
        save_response(
            session=session,
            item=self.item_ok,
            option=self.opt_ok,
            applied_by=self.professor,
            instruction_repeats=5,
        )
        save_response(
            session=session,
            item=self.item_visual_drag,
            option=self.opt_drag,
            applied_by=self.professor,
            instruction_repeats=3,
        )
        complete_session(session)
        self.assertEqual(session.skill_results.get().raw_score, 2)

    def test_large_text_does_not_modify_result(self):
        set_student_features(student=self.student, feature_codes=["VISUAL_LARGE_TEXT"], actor=self.aee)
        session = start_session(enrollment=self.enrollment, instrument=self.instrument, started_by=self.professor)
        self.assertIn("VISUAL_LARGE_TEXT", session.active_features)
        save_response(session=session, item=self.item_ok, option=self.opt_ok, applied_by=self.professor)
        save_response(session=session, item=self.item_visual_drag, option=self.opt_drag, applied_by=self.professor)
        complete_session(session)
        self.assertEqual(session.skill_results.get().status_code, "demonstrated")


class PermissionPrivacyTests(AccessibilityFixtureTestCase):
    def test_teacher_cannot_change_accessibility_profile(self):
        self.assertFalse(can_change_accessibility_profile(self.professor, self.student))
        client = Client()
        client.login(username="prof_a11y", password="pass12345")
        response = client.post(
            reverse("teacher:accessibility_update", args=[self.student.pk]),
            {"features": ["VISUAL_LARGE_TEXT"]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            StudentAccessibilityProfile.objects.filter(student=self.student, feature_links__is_active=True).exists()
        )

    def test_other_school_cannot_access_student(self):
        client = Client()
        client.login(username="prof_b11y", password="pass12345")
        response = client.get(reverse("teacher:student", args=[self.student.pk]))
        self.assertEqual(response.status_code, 302)

    def test_sensitive_data_not_in_network_dashboard(self):
        set_student_features(student=self.student, feature_codes=["VISUAL_SCREEN_READER"], actor=self.aee)
        stats = network_accessibility_stats()
        payload = str(stats)
        self.assertNotIn("SCREEN_READER", payload)
        self.assertNotIn(self.student.full_name, payload)
        self.assertNotIn("autismo", payload.lower())
        self.assertIn("sessions_with_accessibility", stats)


class HistoryVersionTests(AccessibilityFixtureTestCase):
    def test_historical_assessment_preserves_variant(self):
        set_student_features(student=self.student, feature_codes=["MOTOR_NO_DRAG"], actor=self.aee)
        session = start_session(enrollment=self.enrollment, instrument=self.instrument, started_by=self.professor)
        save_response(session=session, item=self.item_ok, option=self.opt_ok, applied_by=self.professor)
        save_response(session=session, item=self.item_visual_drag, option=self.opt_drag, applied_by=self.professor)
        complete_session(session)
        response = session.responses.get(item=self.item_visual_drag)
        self.assertEqual(response.variant_used_id, self.variant_eq.pk)
        self.assertEqual(response.variant_version, 1)
        self.assertEqual(response.variant_name_snapshot, "NoDrag")

        # Mutate live variant — history must stay
        self.variant_eq.instruction_text = "Texto novo 2028"
        self.variant_eq.version = 2
        self.variant_eq.save()
        response.refresh_from_db()
        self.assertEqual(response.variant_version, 1)
        self.assertEqual(response.variant_name_snapshot, "NoDrag")

    def test_alternative_variant_identified(self):
        alt = AssessmentItemVariant.objects.create(
            parent_item=self.item_visual_drag,
            name="Mediated",
            version=1,
            instruction_text="Mediação oral da associação.",
            equivalence_status=AssessmentItemVariant.EquivalenceStatus.ALTERNATIVE,
            adaptation_type=AssessmentItemVariant.AdaptationType.PEDAGOGICAL_MODIFICATION,
            pedagogical_approval_status=AssessmentItemVariant.ApprovalStatus.PUBLISHED,
            justification="Estudante precisa de mediação oral sem alterar objetivo de rima.",
            active=True,
        )
        alt.supported_features.add(self.features["MOTOR_NO_DRAG"])
        self.variant_eq.active = False
        self.variant_eq.save()
        set_student_features(student=self.student, feature_codes=["MOTOR_NO_DRAG"], actor=self.aee)
        resolved = self.resolver.resolve_item(student=self.student, assessment_item=self.item_visual_drag)
        self.assertEqual(resolved.equivalence, AssessmentResponse.EquivalenceApplied.ALTERNATIVE)

    def test_pedagogical_modification_requires_justification(self):
        variant = AssessmentItemVariant(
            parent_item=self.item_ok,
            name="Easier",
            version=1,
            equivalence_status=AssessmentItemVariant.EquivalenceStatus.NOT_EQUIVALENT,
            adaptation_type=AssessmentItemVariant.AdaptationType.PEDAGOGICAL_MODIFICATION,
            pedagogical_approval_status=AssessmentItemVariant.ApprovalStatus.DRAFT,
            justification="",
        )
        with self.assertRaises(ValidationError):
            variant.full_clean()
