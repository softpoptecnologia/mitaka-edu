"""Edital alignment: public page, family portal, implantation."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, UserProfile
from apps.adoption.services import ensure_formation_catalog
from apps.schools.models import Classroom, Municipality, School, SchoolYear
from apps.students.models import Enrollment, FamilyLink, Student

User = get_user_model()


class ChallengeAlignmentTests(TestCase):
    def setUp(self):
        for code, name in Role.Code.choices:
            Role.objects.get_or_create(code=code, defaults={"name": name})
        self.municipality = Municipality.objects.create(name="Jucati", slug="jucati", state="PE")
        self.year = SchoolYear.objects.create(year=2026, label="2026", is_active=True)
        self.school = School.objects.create(municipality=self.municipality, name="EMEI Sol", code="S1")
        self.classroom = Classroom.objects.create(
            school=self.school, school_year=self.year, name="Infantil V A", grade_label="Infantil V"
        )
        self.luna = Student.objects.create(full_name="Luna Ferreira", external_code="F001", birth_date=date(2020, 3, 1))
        Enrollment.objects.create(student=self.luna, classroom=self.classroom, school_year=self.year)
        self.other = Student.objects.create(full_name="Outra Criança", external_code="F002", birth_date=date(2020, 4, 1))
        Enrollment.objects.create(student=self.other, classroom=self.classroom, school_year=self.year)

        self.familia = User.objects.create_user(username="fam1", password="pass12345", first_name="Lúcia")
        UserProfile.objects.update_or_create(
            user=self.familia,
            defaults={"role": Role.objects.get(code=Role.Code.FAMILIA)},
        )
        FamilyLink.objects.create(user=self.familia, student=self.luna)

        self.secretaria = User.objects.create_user(username="sec_align", password="pass12345")
        UserProfile.objects.update_or_create(
            user=self.secretaria,
            defaults={"role": Role.objects.get(code=Role.Code.SECRETARIA)},
        )
        self.professor = User.objects.create_user(username="prof_align", password="pass12345")
        UserProfile.objects.update_or_create(
            user=self.professor,
            defaults={"role": Role.objects.get(code=Role.Code.PROFESSOR), "school": self.school},
        )

    def test_public_home_explains_challenge(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Público-alvo")
        self.assertContains(response, "Sondagem lúdica")
        self.assertContains(response, "Famílias")

    def test_family_sees_only_linked_child(self):
        self.client.login(username="fam1", password="pass12345")
        home = self.client.get(reverse("family:home"))
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, "Luna Ferreira")
        self.assertNotContains(home, "Outra Criança")
        ok = self.client.get(reverse("family:child", args=[self.luna.pk]))
        self.assertEqual(ok.status_code, 200)
        blocked = self.client.get(reverse("family:child", args=[self.other.pk]))
        self.assertEqual(blocked.status_code, 302)

    def test_family_cannot_open_management(self):
        self.client.login(username="fam1", password="pass12345")
        self.assertEqual(self.client.get(reverse("management:dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("secretaria:dashboard")).status_code, 403)

    def test_family_login_lands_on_family_home(self):
        self.client.login(username="fam1", password="pass12345")
        response = self.client.get(reverse("home"), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("family:home"))

    def test_secretaria_opens_implantation_and_usage(self):
        ensure_formation_catalog()
        self.client.login(username="sec_align", password="pass12345")
        self.assertEqual(self.client.get(reverse("adoption:implantation")).status_code, 200)
        self.assertEqual(self.client.get(reverse("adoption:usage")).status_code, 200)
        self.assertEqual(self.client.get(reverse("adoption:formations")).status_code, 200)

    def test_professor_cannot_open_implantation(self):
        self.client.login(username="prof_align", password="pass12345")
        self.assertEqual(self.client.get(reverse("adoption:implantation")).status_code, 403)
