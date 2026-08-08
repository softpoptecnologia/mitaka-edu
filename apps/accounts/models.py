"""Accounts: custom user, roles and profiles."""
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class Role(models.Model):
    class Code(models.TextChoices):
        SUPERADMIN = "SUPERADMIN", "Superadministrador"
        SECRETARIA = "SECRETARIA", "Secretaria Municipal"
        TECNICO = "TECNICO", "Técnico Pedagógico"
        GESTOR = "GESTOR", "Gestor Escolar"
        COORDENADOR = "COORDENADOR", "Coordenador Pedagógico"
        PROFESSOR = "PROFESSOR", "Professor"
        AEE = "AEE", "Atendimento Educacional Especializado"

    code = models.CharField(max_length=32, choices=Code.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_network_wide(self) -> bool:
        return self.code in {
            self.Code.SUPERADMIN,
            self.Code.SECRETARIA,
            self.Code.TECNICO,
        }

    @property
    def is_school_scoped(self) -> bool:
        return self.code in {
            self.Code.GESTOR,
            self.Code.COORDENADOR,
            self.Code.AEE,
        }

    @property
    def is_teacher(self) -> bool:
        return self.code == self.Code.PROFESSOR

    @property
    def is_aee(self) -> bool:
        return self.code == self.Code.AEE


class User(AbstractUser):
    class Meta:
        ordering = ["username"]

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    @property
    def profile(self):
        return getattr(self, "userprofile", None)

    @property
    def role_code(self) -> str | None:
        profile = self.profile
        if profile and profile.role_id:
            return profile.role.code
        return None

    def has_role(self, *codes: str) -> bool:
        return self.role_code in codes


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="profiles", null=True, blank=True)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profiles",
    )
    display_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "Perfil de usuário"
        verbose_name_plural = "Perfis de usuários"

    def __str__(self) -> str:
        return self.display_name or str(self.user)

    @property
    def greeting_name(self) -> str:
        if self.display_name:
            return self.display_name
        if self.user.first_name:
            return self.user.first_name
        return self.user.username
