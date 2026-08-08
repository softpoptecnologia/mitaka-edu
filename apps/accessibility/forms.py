from django import forms

from apps.accessibility.models import AccessibilityFeature, StudentSupportPlan, StudentSupportStrategy
from apps.core.forms import MitakaModelForm
from apps.schools.models import SchoolYear


class SupportPlanForm(MitakaModelForm):
    class Meta:
        model = StudentSupportPlan
        fields = ("school_year", "status", "start_date", "end_date", "notes")
        labels = {
            "school_year": "Ano letivo",
            "status": "Situação",
            "start_date": "Início",
            "end_date": "Término",
            "notes": "Notas pedagógicas",
        }
        help_texts = {
            "notes": "Estratégias de acesso e apoio. Sem conteúdo clínico.",
        }
        widgets = {
            "school_year": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["school_year"].queryset = SchoolYear.objects.all().order_by("-year")


class SupportStrategyForm(MitakaModelForm):
    class Meta:
        model = StudentSupportStrategy
        fields = ("strategy", "accessibility_feature", "notes")
        labels = {
            "strategy": "Estratégia",
            "accessibility_feature": "Recurso de acessibilidade",
            "notes": "Notas",
        }
        widgets = {
            "strategy": forms.TextInput(attrs={"class": "form-control"}),
            "accessibility_feature": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["accessibility_feature"].queryset = AccessibilityFeature.objects.filter(is_active=True)
        self.fields["accessibility_feature"].required = False
        self.fields["notes"].required = False
