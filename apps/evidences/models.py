"""Learning evidence records."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class Evidence(TimeStampedModel, SoftDeleteModel):
    class FileType(models.TextChoices):
        PHOTO = "photo", "Foto"
        AUDIO = "audio", "Áudio"
        VIDEO = "video", "Vídeo"
        TEXT = "text", "Observação textual"
        NONE = "none", "Sem arquivo"

    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.PROTECT,
        related_name="evidences",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="evidences",
    )
    skill = models.ForeignKey(
        "curriculum.Skill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidences",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidences",
    )
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="evidences/%Y/%m/", blank=True, null=True)
    file_type = models.CharField(max_length=20, choices=FileType.choices, default=FileType.NONE)
    recorded_at = models.DateTimeField(auto_now_add=True)
    visible_to_family = models.BooleanField(
        default=False,
        help_text="Se marcado, a família pode ver esta evidência no portal (sem dados clínicos).",
    )

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = "Evidência"
        verbose_name_plural = "Evidências"

    def __str__(self) -> str:
        return f"Evidência {self.student} ({self.recorded_at:%d/%m/%Y})"
