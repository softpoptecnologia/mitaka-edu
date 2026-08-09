from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.core.forms import MitakaModelForm
from apps.curriculum.models import Skill
from apps.evidences.models import Evidence


class EvidenceForm(MitakaModelForm):
    class Meta:
        model = Evidence
        fields = ("skill", "description", "file", "visible_to_family")
        labels = {
            "skill": "Habilidade",
            "description": "Observação",
            "file": "Arquivo",
            "visible_to_family": "Compartilhar com a família",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "Descreva a observação"}),
            "skill": forms.Select(attrs={"class": "form-select"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "visible_to_family": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skill"].queryset = Skill.objects.all()
        self.fields["skill"].required = False
        self.fields["description"].required = False
        self.fields["file"].required = False

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("description") and not cleaned.get("file"):
            raise ValidationError("Informe uma observação ou anexe um arquivo.")
        uploaded = cleaned.get("file")
        if uploaded and uploaded.size > settings.MAX_EVIDENCE_FILE_SIZE:
            raise ValidationError("Arquivo excede o tamanho máximo permitido (8 MB).")
        return cleaned
