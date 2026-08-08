"""Simplified pedagogical planning assisted by data."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class PedagogicalPlan(TimeStampedModel, SoftDeleteModel):
    classroom = models.ForeignKey(
        "schools.Classroom",
        on_delete=models.CASCADE,
        related_name="plans",
    )
    title = models.CharField(max_length=200)
    skill = models.ForeignKey(
        "curriculum.Skill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plans",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="plans",
    )
    notes = models.TextField(blank=True)
    classroom_intervention = models.ForeignKey(
        "interventions.ClassroomIntervention",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plans",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class PlanActivity(TimeStampedModel):
    plan = models.ForeignKey(PedagogicalPlan, on_delete=models.CASCADE, related_name="activities")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_done = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Atividade do plano"
        verbose_name_plural = "Atividades do plano"

    def __str__(self) -> str:
        return self.title
