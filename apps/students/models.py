"""Students and enrollments — longitudinal identity separated from yearly context."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class Student(TimeStampedModel, SoftDeleteModel):
    full_name = models.CharField(max_length=200)
    birth_date = models.DateField(null=True, blank=True)
    external_code = models.CharField(
        max_length=64,
        unique=True,
        help_text="Identificador municipal/matrícula permanente",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self) -> str:
        return self.full_name

    def current_enrollment(self):
        return (
            self.enrollments.filter(is_active=True, status=Enrollment.Status.ACTIVE)
            .select_related("classroom", "school_year", "classroom__school")
            .order_by("-school_year__year")
            .first()
        )


class Enrollment(TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        TRANSFERRED = "transferred", "Transferida"
        COMPLETED = "completed", "Concluída"
        CANCELLED = "cancelled", "Cancelada"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    classroom = models.ForeignKey("schools.Classroom", on_delete=models.PROTECT, related_name="enrollments")
    school_year = models.ForeignKey("schools.SchoolYear", on_delete=models.PROTECT, related_name="enrollments")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-school_year__year", "student__full_name"]
        unique_together = [("student", "school_year")]

    def __str__(self) -> str:
        return f"{self.student} — {self.classroom} ({self.school_year})"

    @property
    def school(self):
        return self.classroom.school


class FamilyLink(TimeStampedModel, SoftDeleteModel):
    """Responsible adult linked to a child — pedagogical accompaniment only."""

    class Kinship(models.TextChoices):
        MOTHER = "mae", "Mãe"
        FATHER = "pai", "Pai"
        GRANDPARENT = "avo", "Avó/Avô"
        GUARDIAN = "responsavel", "Responsável"
        OTHER = "outro", "Outro"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="family_links",
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="family_links")
    kinship = models.CharField(max_length=20, choices=Kinship.choices, default=Kinship.GUARDIAN)

    class Meta:
        unique_together = [("user", "student")]
        ordering = ["student__full_name"]
        verbose_name = "Vínculo familiar"
        verbose_name_plural = "Vínculos familiares"

    def __str__(self) -> str:
        return f"{self.user} → {self.student}"


class ImportJob(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        RUNNING = "running", "Em execução"
        DONE = "done", "Concluído"
        FAILED = "failed", "Falhou"

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="import_jobs",
    )
    school_year = models.ForeignKey("schools.SchoolYear", on_delete=models.PROTECT, related_name="import_jobs")
    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_rows = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Import {self.file_name} ({self.status})"


class ImportError(models.Model):
    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="errors")
    row_number = models.PositiveIntegerField()
    message = models.TextField()
    raw_data = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"Linha {self.row_number}: {self.message}"
