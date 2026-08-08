from django import forms

from apps.core.forms import MitakaModelForm
from apps.curriculum.models import DevelopmentDimension, MatrixVersion, PedagogicalMatrix, Skill, StatusLabelConfig


def _control(widget):
    widget.attrs["class"] = f"{widget.attrs.get('class', '')} form-control".strip()
    return widget


def _select():
    return forms.Select(attrs={"class": "form-select"})


class MatrixForm(MitakaModelForm):
    class Meta:
        model = PedagogicalMatrix
        fields = ("name", "description", "is_active")
        labels = {"name": "Nome", "description": "Descrição", "is_active": "Matriz ativa"}
        widgets = {
            "name": _control(forms.TextInput()),
            "description": _control(forms.Textarea(attrs={"rows": 3})),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class MatrixVersionForm(MitakaModelForm):
    class Meta:
        model = MatrixVersion
        fields = ("matrix", "version_label", "framework_reference", "notes")
        labels = {
            "matrix": "Matriz",
            "version_label": "Versão",
            "framework_reference": "Referência curricular",
            "notes": "Notas",
        }
        help_texts = {
            "framework_reference": "Ex.: Currículo de Pernambuco / BNCC — Língua Portuguesa Anos Iniciais",
        }
        widgets = {
            "matrix": _select(),
            "version_label": _control(forms.TextInput()),
            "framework_reference": _control(forms.TextInput()),
            "notes": _control(forms.Textarea(attrs={"rows": 3})),
        }


class DimensionForm(MitakaModelForm):
    class Meta:
        model = DevelopmentDimension
        fields = ("matrix_version", "code", "name", "practice_axis", "description", "order")
        labels = {
            "matrix_version": "Versão da matriz",
            "code": "Código",
            "name": "Nome",
            "practice_axis": "Eixo / prática",
            "description": "Descrição",
            "order": "Ordem",
        }
        help_texts = {
            "practice_axis": "Ex.: Oralidade, Análise linguística",
        }
        widgets = {
            "matrix_version": _select(),
            "code": _control(forms.TextInput()),
            "name": _control(forms.TextInput()),
            "practice_axis": _control(forms.TextInput()),
            "description": _control(forms.Textarea(attrs={"rows": 3})),
            "order": _control(forms.NumberInput()),
        }


class SkillForm(MitakaModelForm):
    class Meta:
        model = Skill
        fields = ("dimension", "code", "bncc_code", "name", "knowledge_object", "description", "curriculum_notes", "order")
        labels = {
            "dimension": "Dimensão",
            "code": "Código interno",
            "bncc_code": "Código PE / BNCC",
            "name": "Nome",
            "knowledge_object": "Objeto de conhecimento",
            "description": "Descrição",
            "curriculum_notes": "Orientação curricular",
            "order": "Ordem",
        }
        help_texts = {
            "bncc_code": "Ex.: EF01LP06PE",
            "curriculum_notes": "Orientação pedagógica alinhada ao Currículo de Pernambuco.",
        }
        widgets = {
            "dimension": _select(),
            "code": _control(forms.TextInput()),
            "bncc_code": _control(forms.TextInput()),
            "name": _control(forms.TextInput()),
            "knowledge_object": _control(forms.TextInput()),
            "description": _control(forms.Textarea(attrs={"rows": 3})),
            "curriculum_notes": _control(forms.Textarea(attrs={"rows": 3})),
            "order": _control(forms.NumberInput()),
        }


DEFAULT_STATUS_LABELS = [
    ("not_observed", "Não observado", 0),
    ("needs_support", "Necessita maior mediação", 1),
    ("developing", "Em desenvolvimento", 2),
    ("demonstrated", "Habilidade demonstrada", 3),
]


def ensure_default_status_labels(version: MatrixVersion) -> None:
    for order, (code, label, severity) in enumerate(DEFAULT_STATUS_LABELS):
        StatusLabelConfig.objects.get_or_create(
            matrix_version=version,
            code=code,
            defaults={"label": label, "severity": severity, "order": order},
        )
