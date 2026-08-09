"""Intervention templates and student/classroom interventions."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class InterventionTemplate(TimeStampedModel, SoftDeleteModel):
    skill = models.ForeignKey(
        "curriculum.Skill",
        on_delete=models.CASCADE,
        related_name="intervention_templates",
    )
    title = models.CharField(max_length=200)
    objective = models.TextField()
    suggested_activities = models.TextField(help_text="Uma atividade por linha")
    suggested_duration_days = models.PositiveIntegerField(default=14)
    suggested_activity_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Duração sugerida da atividade em uma aula (minutos).",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title

    def activities_list(self) -> list[str]:
        return [line.strip() for line in self.suggested_activities.splitlines() if line.strip()]


class InterventionStatus(models.TextChoices):
    PLANNED = "planned", "Planejada"
    IN_PROGRESS = "in_progress", "Em andamento"
    COMPLETED = "completed", "Concluída"
    CANCELLED = "cancelled", "Cancelada"


class FollowupResult(models.TextChoices):
    PROGRESSED = "progressed", "Avançou"
    NEEDS_MORE_SUPPORT = "needs_more_support", "Ainda precisa de apoio"
    NOT_OBSERVED = "not_observed", "Não participou / não foi possível observar"


class StudentIntervention(TimeStampedModel, SoftDeleteModel):
    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.PROTECT,
        related_name="interventions",
    )
    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="interventions")
    skill = models.ForeignKey("curriculum.Skill", on_delete=models.PROTECT, related_name="student_interventions")
    template = models.ForeignKey(
        InterventionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_interventions",
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_interventions",
    )
    objective = models.TextField()
    activities = models.TextField(blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=InterventionStatus.choices, default=InterventionStatus.PLANNED)
    observation = models.TextField(blank=True)
    classroom_intervention = models.ForeignKey(
        "interventions.ClassroomIntervention",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_links",
    )
    followup_result = models.CharField(
        max_length=32,
        choices=FollowupResult.choices,
        blank=True,
    )
    followup_recorded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Intervenção {self.student} — {self.skill}"

    @property
    def has_followup(self) -> bool:
        return bool(self.followup_result)


class ClassroomIntervention(TimeStampedModel, SoftDeleteModel):
    classroom = models.ForeignKey(
        "schools.Classroom",
        on_delete=models.PROTECT,
        related_name="interventions",
    )
    skill = models.ForeignKey("curriculum.Skill", on_delete=models.PROTECT, related_name="classroom_interventions")
    template = models.ForeignKey(
        InterventionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classroom_interventions",
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="classroom_interventions",
    )
    objective = models.TextField()
    activities = models.TextField(blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=InterventionStatus.choices, default=InterventionStatus.PLANNED)
    observation = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Intervenção turma {self.classroom} — {self.skill}"
