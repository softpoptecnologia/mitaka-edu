from django import forms

from apps.core.forms import MitakaModelForm
from apps.curriculum.models import Skill
from apps.interventions.models import InterventionTemplate, StudentIntervention


class StudentInterventionForm(MitakaModelForm):
    class Meta:
        model = StudentIntervention
        fields = ("skill", "objective", "activities", "starts_on", "ends_on", "observation", "status")
        labels = {
            "skill": "Habilidade",
            "objective": "Objetivo",
            "activities": "Atividades",
            "starts_on": "Início",
            "ends_on": "Término",
            "observation": "Observações",
            "status": "Situação",
        }
        widgets = {
            "skill": forms.Select(attrs={"class": "form-select"}),
            "objective": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "activities": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "starts_on": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "ends_on": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "observation": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skill"].queryset = Skill.objects.all()


class InterventionTemplateForm(MitakaModelForm):
    class Meta:
        model = InterventionTemplate
        fields = ("skill", "title", "objective", "suggested_activities", "suggested_duration_days", "notes")
        labels = {
            "skill": "Habilidade",
            "title": "Título",
            "objective": "Objetivo",
            "suggested_activities": "Atividades sugeridas",
            "suggested_duration_days": "Duração sugerida (dias)",
            "notes": "Notas",
        }
        help_texts = {
            "suggested_activities": "Uma atividade por linha.",
        }
        widgets = {
            "skill": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "objective": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "suggested_activities": forms.Textarea(attrs={"rows": 5, "class": "form-control"}),
            "suggested_duration_days": forms.NumberInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }
