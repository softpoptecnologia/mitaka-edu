"""Continuing education catalog for the municipal network."""
from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class FormationProgram(TimeStampedModel, SoftDeleteModel):
    class Audience(models.TextChoices):
        PROFESSOR = "professor", "Professoras e professores"
        COORDENACAO = "coordenacao", "Coordenação pedagógica"
        GESTAO = "gestao", "Equipe gestora escolar"
        TECNICO = "tecnico", "Equipe técnica da Secretaria"
        FAMILIA = "familia", "Famílias acompanhadas pela rede"

    class Modality(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial na escola / SME"
        HIBRIDO = "hibrido", "Híbrido"
        EAD = "ead", "A distância (PWA / tablet)"

    title = models.CharField(max_length=200)
    audience = models.CharField(max_length=20, choices=Audience.choices)
    objective = models.TextField()
    duration_hours = models.PositiveSmallIntegerField(default=4)
    modality = models.CharField(max_length=20, choices=Modality.choices, default=Modality.HIBRIDO)
    skill = models.ForeignKey(
        "curriculum.Skill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="formation_programs",
    )
    agenda = models.TextField(help_text="Um tópico por linha")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "Formação continuada"
        verbose_name_plural = "Formações continuadas"

    def __str__(self) -> str:
        return self.title

    def agenda_list(self) -> list[str]:
        return [line.strip() for line in self.agenda.splitlines() if line.strip()]
