"""Pedagogical matrix, dimensions, skills and versioning."""
from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class PedagogicalMatrix(TimeStampedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Matriz pedagógica"
        verbose_name_plural = "Matrizes pedagógicas"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def current_version(self):
        return self.versions.filter(is_published=True).order_by("-published_at", "-id").first()


class MatrixVersion(TimeStampedModel):
    matrix = models.ForeignKey(PedagogicalMatrix, on_delete=models.CASCADE, related_name="versions")
    version_label = models.CharField(max_length=50)
    notes = models.TextField(blank=True)
    framework_reference = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Ex.: Currículo de Pernambuco / BNCC — Língua Portuguesa Anos Iniciais",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-id"]
        unique_together = [("matrix", "version_label")]

    def __str__(self) -> str:
        return f"{self.matrix} — {self.version_label}"


class DevelopmentDimension(TimeStampedModel):
    matrix_version = models.ForeignKey(MatrixVersion, on_delete=models.CASCADE, related_name="dimensions")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    practice_axis = models.CharField(
        max_length=100,
        blank=True,
        help_text="Eixo/prática de linguagem do Currículo PE (ex.: Oralidade, Análise linguística)",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        unique_together = [("matrix_version", "code")]

    def __str__(self) -> str:
        return self.name


class Skill(TimeStampedModel):
    dimension = models.ForeignKey(DevelopmentDimension, on_delete=models.CASCADE, related_name="skills")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    bncc_code = models.CharField(
        max_length=40,
        blank=True,
        help_text="Código Currículo PE / BNCC (ex.: EF01LP06PE)",
    )
    knowledge_object = models.CharField(max_length=200, blank=True)
    curriculum_notes = models.TextField(
        blank=True,
        help_text="Orientação pedagógica alinhada ao Currículo de Pernambuco",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        unique_together = [("dimension", "code")]

    def __str__(self) -> str:
        if self.bncc_code:
            return f"{self.bncc_code} — {self.name}"
        return self.name

    @property
    def matrix_version(self):
        return self.dimension.matrix_version


class SkillProgression(TimeStampedModel):
    from_skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="next_links")
    to_skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="prev_links")
    order = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = [("from_skill", "to_skill")]

    def __str__(self) -> str:
        return f"{self.from_skill} → {self.to_skill}"


class StatusLabelConfig(TimeStampedModel):
    """Configurable pedagogical status nomenclature."""

    matrix_version = models.ForeignKey(MatrixVersion, on_delete=models.CASCADE, related_name="status_labels")
    code = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    severity = models.PositiveSmallIntegerField(
        default=0,
        help_text="0=não observado, maior = mais atenção necessária ou progresso",
    )
    color_token = models.CharField(max_length=30, blank=True)
    icon = models.CharField(max_length=30, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "code"]
        unique_together = [("matrix_version", "code")]

    def __str__(self) -> str:
        return self.label

