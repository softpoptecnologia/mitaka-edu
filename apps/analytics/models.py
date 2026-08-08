"""Analytics snapshots and student skill status."""
from django.db import models

from apps.core.models import TimeStampedModel

METRIC_LABELS = {
    "attention_pct": "% em atenção",
    "assessment_coverage_pct": "% de cobertura avaliativa",
}


class StudentSkillStatus(TimeStampedModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="skill_statuses")
    skill = models.ForeignKey("curriculum.Skill", on_delete=models.CASCADE, related_name="student_statuses")
    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="skill_statuses",
    )
    status_code = models.CharField(max_length=50)
    status_label = models.CharField(max_length=100)
    needs_attention = models.BooleanField(default=False)
    last_session = models.ForeignKey(
        "assessments.AssessmentSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resulting_statuses",
    )
    raw_score = models.IntegerField(null=True, blank=True)
    max_score = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = [("student", "skill")]
        verbose_name = "Situação da habilidade"
        verbose_name_plural = "Situações das habilidades"
        ordering = ["skill__name"]

    def __str__(self) -> str:
        return f"{self.student} — {self.skill}: {self.status_label}"


class AggregatedIndicator(TimeStampedModel):
    class Scope(models.TextChoices):
        NETWORK = "network", "Rede"
        SCHOOL = "school", "Escola"
        CLASSROOM = "classroom", "Turma"
        STUDENT = "student", "Estudante"

    scope = models.CharField(max_length=20, choices=Scope.choices)
    school_year = models.ForeignKey(
        "schools.SchoolYear",
        on_delete=models.CASCADE,
        related_name="indicators",
    )
    municipality = models.ForeignKey(
        "schools.Municipality",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="indicators",
    )
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="indicators",
    )
    classroom = models.ForeignKey(
        "schools.Classroom",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="indicators",
    )
    skill = models.ForeignKey(
        "curriculum.Skill",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="indicators",
    )
    metric_key = models.CharField(max_length=100)
    metric_value = models.FloatField(default=0)
    sample_size = models.PositiveIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["scope", "metric_key"]),
            models.Index(fields=["school_year", "scope"]),
        ]
        ordering = ["-updated_at"]

    @property
    def metric_label(self) -> str:
        return METRIC_LABELS.get(self.metric_key, self.metric_key)

    def __str__(self) -> str:
        return f"{self.scope}:{self.metric_key}={self.metric_value}"
