"""Schools domain: municipality, schools, years, classrooms."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class Municipality(TimeStampedModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    state = models.CharField(max_length=2, default="PE")

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name}/{self.state}"


class School(TimeStampedModel, SoftDeleteModel):
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT, related_name="schools")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SchoolYear(TimeStampedModel):
    year = models.PositiveIntegerField(unique=True)
    label = models.CharField(max_length=50, blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ["-year"]

    def __str__(self) -> str:
        return self.label or str(self.year)

    def save(self, *args, **kwargs):
        if self.is_active:
            SchoolYear.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)
        if not self.label:
            self.label = str(self.year)
        super().save(*args, **kwargs)


class Classroom(TimeStampedModel, SoftDeleteModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="classrooms")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.PROTECT, related_name="classrooms")
    name = models.CharField(max_length=100)
    grade_label = models.CharField(max_length=100, help_text="Ex.: Infantil V, 1º Ano")
    shift = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["school__name", "name"]
        unique_together = [("school", "school_year", "name")]

    def __str__(self) -> str:
        return f"{self.name} ({self.school_year})"


class TeacherClassroom(TimeStampedModel):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_classrooms",
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="teacher_links")
    is_primary = models.BooleanField(default=True)

    class Meta:
        unique_together = [("teacher", "classroom")]
        verbose_name = "Vínculo professor-turma"
        verbose_name_plural = "Vínculos professor-turma"

    def __str__(self) -> str:
        return f"{self.teacher} → {self.classroom}"
