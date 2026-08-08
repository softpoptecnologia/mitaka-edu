"""Form helpers: rótulos e selects em português."""
from django import forms

SELECT_EMPTY = "Selecione..."


def localize_form_fields(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(field, forms.ModelChoiceField) and field.empty_label is not None:
            field.empty_label = SELECT_EMPTY
        elif isinstance(field, forms.ChoiceField):
            choices = list(field.choices)
            if choices and choices[0][0] in ("", None) and str(choices[0][1]).startswith("-"):
                field.choices = [("", SELECT_EMPTY), *choices[1:]]


class MitakaForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        localize_form_fields(self)


class MitakaModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        localize_form_fields(self)
