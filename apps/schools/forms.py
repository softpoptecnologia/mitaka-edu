from django import forms
from django.utils.text import slugify

from apps.core.forms import MitakaModelForm
from apps.schools.models import Classroom, Municipality, School, SchoolYear


def _control(widget):
    css = widget.attrs.get("class", "")
    widget.attrs["class"] = f"{css} form-control".strip()
    return widget


def _select(widget=None):
    widget = widget or forms.Select()
    widget.attrs["class"] = "form-select"
    return widget


class MunicipalityForm(MitakaModelForm):
    class Meta:
        model = Municipality
        fields = ("name", "state", "slug")
        labels = {"name": "Nome", "state": "UF", "slug": "Identificador"}
        help_texts = {
            "state": "Sigla do estado, ex.: PE.",
            "slug": "Gerado automaticamente se vazio.",
        }
        widgets = {
            "name": _control(forms.TextInput()),
            "state": _control(forms.TextInput(attrs={"maxlength": 2})),
            "slug": _control(forms.TextInput()),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        name = self.cleaned_data.get("name") or ""
        return slug or slugify(name)[:50]


class SchoolYearForm(MitakaModelForm):
    class Meta:
        model = SchoolYear
        fields = ("year", "label", "starts_on", "ends_on", "is_active")
        labels = {
            "year": "Ano",
            "label": "Rótulo",
            "starts_on": "Início",
            "ends_on": "Término",
            "is_active": "Ano ativo",
        }
        widgets = {
            "year": _control(forms.NumberInput()),
            "label": _control(forms.TextInput()),
            "starts_on": _control(forms.DateInput(attrs={"type": "date"})),
            "ends_on": _control(forms.DateInput(attrs={"type": "date"})),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SchoolForm(MitakaModelForm):
    class Meta:
        model = School
        fields = ("municipality", "name", "code", "address")
        labels = {
            "municipality": "Município",
            "name": "Nome",
            "code": "Código",
            "address": "Endereço",
        }
        widgets = {
            "municipality": _select(),
            "name": _control(forms.TextInput()),
            "code": _control(forms.TextInput()),
            "address": _control(forms.TextInput()),
        }


class ClassroomForm(MitakaModelForm):
    class Meta:
        model = Classroom
        fields = ("school", "school_year", "name", "grade_label", "shift")
        labels = {
            "school": "Escola",
            "school_year": "Ano letivo",
            "name": "Nome da turma",
            "grade_label": "Série / etapa",
            "shift": "Turno",
        }
        help_texts = {
            "grade_label": "Ex.: Infantil V, 1º Ano",
            "shift": "Ex.: Manhã, Tarde",
        }
        widgets = {
            "school": _select(),
            "school_year": _select(),
            "name": _control(forms.TextInput()),
            "grade_label": _control(forms.TextInput()),
            "shift": _control(forms.TextInput()),
        }

    def __init__(self, *args, schools=None, **kwargs):
        super().__init__(*args, **kwargs)
        if schools is not None:
            self.fields["school"].queryset = schools
        self.fields["school_year"].queryset = SchoolYear.objects.all().order_by("-year")
        self.fields["shift"].required = False
