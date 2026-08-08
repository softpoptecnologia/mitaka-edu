"""Functional accessibility profiles and pedagogical support plans.

Stores access/support needs — not clinical diagnoses, CID codes, or medical records.
"""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class AccessibilityCategory(TimeStampedModel):
    class Code(models.TextChoices):
        VISUAL = "VISUAL", "Visual"
        AUDITORY = "AUDITORY", "Auditiva"
        MOTOR = "MOTOR", "Motora"
        COGNITIVE = "COGNITIVE", "Cognitiva / atenção"
        SENSORY = "SENSORY", "Sensorial"
        COMMUNICATION = "COMMUNICATION", "Comunicação"

    code = models.CharField(max_length=32, choices=Code.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Categoria de acessibilidade"
        verbose_name_plural = "Categorias de acessibilidade"

    def __str__(self) -> str:
        return self.name


class AccessibilityFeature(TimeStampedModel):
    """Reusable functional access/support feature (extensible without schema changes)."""

    class Code(models.TextChoices):
        VISUAL_SCREEN_READER = "VISUAL_SCREEN_READER", "Leitor de tela"
        VISUAL_HIGH_CONTRAST = "VISUAL_HIGH_CONTRAST", "Alto contraste"
        VISUAL_LARGE_TEXT = "VISUAL_LARGE_TEXT", "Texto ampliado"
        AUDITORY_CAPTIONS = "AUDITORY_CAPTIONS", "Legendas"
        AUDITORY_VISUAL_INSTRUCTION = "AUDITORY_VISUAL_INSTRUCTION", "Instrução visual"
        AUDITORY_LIBRAS = "AUDITORY_LIBRAS", "Libras"
        MOTOR_LARGE_TARGET = "MOTOR_LARGE_TARGET", "Alvos ampliados"
        MOTOR_KEYBOARD = "MOTOR_KEYBOARD", "Navegação por teclado"
        MOTOR_NO_DRAG = "MOTOR_NO_DRAG", "Sem arrastar e soltar"
        COGNITIVE_SHORT_INSTRUCTIONS = "COGNITIVE_SHORT_INSTRUCTIONS", "Instruções curtas"
        COGNITIVE_EXTRA_TIME = "COGNITIVE_EXTRA_TIME", "Tempo ampliado"
        COGNITIVE_STEP_BY_STEP = "COGNITIVE_STEP_BY_STEP", "Instruções passo a passo"
        COGNITIVE_NO_TIME_LIMIT = "COGNITIVE_NO_TIME_LIMIT", "Sem limite rígido de tempo"
        COGNITIVE_REPEAT_INSTRUCTIONS = "COGNITIVE_REPEAT_INSTRUCTIONS", "Repetição de instruções"
        SENSORY_REDUCED_MOTION = "SENSORY_REDUCED_MOTION", "Redução de animações"
        SENSORY_REDUCED_STIMULUS = "SENSORY_REDUCED_STIMULUS", "Redução de estímulos"

    category = models.ForeignKey(
        AccessibilityCategory,
        on_delete=models.PROTECT,
        related_name="features",
    )
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    css_class = models.CharField(
        max_length=64,
        blank=True,
        help_text="Classe CSS opcional aplicada no player (ex.: a11y-large-text).",
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["category__order", "order", "name"]
        permissions = [
            ("view_student_accessibility", "Pode ver recursos de acessibilidade do estudante"),
            ("change_student_accessibility", "Pode alterar perfil de acessibilidade do estudante"),
            ("manage_support_plan", "Pode gerenciar plano de apoio pedagógico"),
        ]

    def __str__(self) -> str:
        return self.name


class StudentAccessibilityProfile(TimeStampedModel, SoftDeleteModel):
    """Pedagogical access profile — functional needs only."""

    student = models.OneToOneField(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="accessibility_profile",
    )
    notes = models.TextField(
        blank=True,
        help_text="Observações pedagógicas sobre acesso e apoio. Não incluir CID, laudos ou dados clínicos.",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_accessibility_profiles",
    )

    class Meta:
        verbose_name = "Perfil de acessibilidade do estudante"
        verbose_name_plural = "Perfis de acessibilidade"

    def __str__(self) -> str:
        return f"Acessibilidade — {self.student}"

    def active_feature_codes(self) -> list[str]:
        return list(
            self.feature_links.filter(is_active=True, feature__is_active=True).values_list(
                "feature__code", flat=True
            )
        )

    def active_features(self):
        return AccessibilityFeature.objects.filter(
            student_links__profile=self,
            student_links__is_active=True,
            is_active=True,
        ).select_related("category")


class StudentAccessibilityFeature(TimeStampedModel):
    profile = models.ForeignKey(
        StudentAccessibilityProfile,
        on_delete=models.CASCADE,
        related_name="feature_links",
    )
    feature = models.ForeignKey(
        AccessibilityFeature,
        on_delete=models.PROTECT,
        related_name="student_links",
    )
    priority = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("profile", "feature")]
        ordering = ["priority", "feature__name"]

    def __str__(self) -> str:
        return f"{self.profile.student} → {self.feature.code}"


class StudentSupportPlan(TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        ACTIVE = "active", "Ativo"
        REVIEW = "review", "Em revisão"
        COMPLETED = "completed", "Concluído"
        ARCHIVED = "archived", "Arquivado"

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="support_plans",
    )
    school_year = models.ForeignKey(
        "schools.SchoolYear",
        on_delete=models.PROTECT,
        related_name="support_plans",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(
        blank=True,
        help_text="Notas pedagógicas do plano de apoio. Sem conteúdo clínico.",
    )
    responsible_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="support_plans",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_support_plans",
    )

    class Meta:
        ordering = ["-start_date", "-created_at"]

    def __str__(self) -> str:
        return f"Plano de apoio — {self.student} ({self.school_year})"


class StudentSupportStrategy(TimeStampedModel):
    support_plan = models.ForeignKey(
        StudentSupportPlan,
        on_delete=models.CASCADE,
        related_name="strategies",
    )
    accessibility_feature = models.ForeignKey(
        AccessibilityFeature,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_strategies",
    )
    strategy = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Estratégia de apoio"
        verbose_name_plural = "Estratégias de apoio"

    def __str__(self) -> str:
        return self.strategy
