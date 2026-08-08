from django import forms

from apps.core.forms import MitakaModelForm
from apps.schools.models import Classroom
from apps.students.models import Enrollment, Student


def _control(widget):
    css = widget.attrs.get("class", "")
    widget.attrs["class"] = f"{css} form-control".strip()
    return widget


def _select(widget=None):
    widget = widget or forms.Select()
    widget.attrs["class"] = "form-select"
    return widget


class StudentForm(MitakaModelForm):
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.none(),
        required=False,
        label="Turma (matrícula inicial)",
        widget=_select(),
        help_text="Opcional na criação. Gera matrícula no ano da turma.",
    )

    class Meta:
        model = Student
        fields = ("full_name", "external_code", "birth_date", "notes")
        labels = {
            "full_name": "Nome completo",
            "external_code": "Matrícula / código",
            "birth_date": "Data de nascimento",
            "notes": "Observações",
        }
        help_texts = {
            "external_code": "Identificador municipal permanente.",
        }
        widgets = {
            "full_name": _control(forms.TextInput()),
            "external_code": _control(forms.TextInput()),
            "birth_date": _control(forms.DateInput(attrs={"type": "date"})),
            "notes": _control(forms.Textarea(attrs={"rows": 3})),
        }

    def __init__(self, *args, classrooms=None, include_classroom=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not include_classroom:
            self.fields.pop("classroom", None)
            return
        if classrooms is not None:
            self.fields["classroom"].queryset = classrooms.select_related("school", "school_year")
        if include_classroom and not getattr(self.instance, "pk", None):
            self.fields["classroom"].required = True
        self.fields["notes"].required = False
        self.fields["birth_date"].required = False


class EnrollmentForm(MitakaModelForm):
    class Meta:
        model = Enrollment
        fields = ("student", "classroom", "school_year", "status", "enrolled_at")
        labels = {
            "student": "Estudante",
            "classroom": "Turma",
            "school_year": "Ano letivo",
            "status": "Situação",
            "enrolled_at": "Data da matrícula",
        }
        widgets = {
            "student": _select(),
            "classroom": _select(),
            "school_year": _select(),
            "status": _select(),
            "enrolled_at": _control(forms.DateInput(attrs={"type": "date"})),
        }

    def __init__(self, *args, students=None, classrooms=None, **kwargs):
        super().__init__(*args, **kwargs)
        if students is not None:
            self.fields["student"].queryset = students
        if classrooms is not None:
            self.fields["classroom"].queryset = classrooms.select_related("school", "school_year")
        self.fields["enrolled_at"].required = False

    def clean(self):
        cleaned = super().clean()
        classroom = cleaned.get("classroom")
        year = cleaned.get("school_year")
        if classroom and not year:
            cleaned["school_year"] = classroom.school_year
            year = classroom.school_year
        if classroom and year and classroom.school_year_id != year.pk:
            self.add_error("school_year", "O ano letivo deve ser o mesmo da turma selecionada.")
        student = cleaned.get("student")
        if student and year:
            qs = Enrollment.objects.filter(student=student, school_year=year)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("school_year", "Já existe matrícula deste estudante neste ano letivo.")
        return cleaned
