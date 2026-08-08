from django import forms

from apps.assessments.models import AssessmentInstrument, AssessmentItem
from apps.core.forms import MitakaForm, MitakaModelForm
from apps.curriculum.models import MatrixVersion, Skill


class InstrumentForm(MitakaModelForm):
    class Meta:
        model = AssessmentInstrument
        fields = ("matrix_version", "skill", "title", "description", "instrument_type", "estimated_minutes", "is_published")
        labels = {
            "matrix_version": "Versão da matriz",
            "skill": "Habilidade",
            "title": "Título",
            "description": "Descrição",
            "instrument_type": "Tipo",
            "estimated_minutes": "Duração estimada (minutos)",
            "is_published": "Publicado",
        }
        widgets = {
            "matrix_version": forms.Select(attrs={"class": "form-select"}),
            "skill": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "instrument_type": forms.Select(attrs={"class": "form-select"}),
            "estimated_minutes": forms.NumberInput(attrs={"class": "form-control"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["matrix_version"].queryset = MatrixVersion.objects.select_related("matrix").order_by("-published_at", "-id")
        self.fields["skill"].queryset = Skill.objects.select_related("dimension").order_by("name")


class InstrumentItemForm(MitakaForm):
    prompt = forms.CharField(label="Enunciado", widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}))
    item_type = forms.ChoiceField(
        label="Tipo",
        choices=[
            (AssessmentItem.ItemType.SINGLE_SELECT, "Seleção simples"),
            (AssessmentItem.ItemType.OBSERVATION_SCALE, "Escala observacional"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    options_text = forms.CharField(
        label="Alternativas",
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control"}),
        help_text="Uma por linha. Use texto|pontos ou texto|* para marcar a correta.",
    )

    def parsed_options(self) -> list[dict]:
        rows = []
        for order, line in enumerate(self.cleaned_data["options_text"].splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            is_correct = False
            if line.endswith("|*"):
                line = line[:-2].strip()
                is_correct = True
                score = 1
            elif "|" in line:
                label, score_raw = line.rsplit("|", 1)
                line = label.strip()
                try:
                    score = int(score_raw.strip())
                except ValueError:
                    score = 0
                is_correct = score > 0
            else:
                score = 0
            rows.append({"label": line, "score_value": score, "is_correct": is_correct, "order": order})
        return rows
