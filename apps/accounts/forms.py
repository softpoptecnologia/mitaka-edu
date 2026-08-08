from django import forms

from apps.accounts.models import Role, User
from apps.core.forms import MitakaForm, MitakaModelForm
from apps.schools.models import Classroom, School, TeacherClassroom


def _control(widget):
    css = widget.attrs.get("class", "")
    widget.attrs["class"] = f"{css} form-control".strip()
    return widget


def _select(widget=None):
    widget = widget or forms.Select()
    widget.attrs["class"] = "form-select"
    return widget


class TeacherForm(MitakaForm):
    first_name = forms.CharField(label="Nome", max_length=150, widget=_control(forms.TextInput()))
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False, widget=_control(forms.TextInput()))
    username = forms.CharField(label="Usuário", max_length=150, widget=_control(forms.TextInput()))
    email = forms.EmailField(label="E-mail", required=False, widget=_control(forms.EmailInput()))
    password = forms.CharField(
        label="Senha",
        required=False,
        widget=_control(forms.PasswordInput()),
        help_text="Obrigatória na criação. Deixe em branco para manter a senha atual.",
    )
    role = forms.ModelChoiceField(label="Papel", queryset=Role.objects.none(), widget=_select())
    school = forms.ModelChoiceField(label="Escola", queryset=School.objects.none(), required=False, widget=_select())
    is_active = forms.BooleanField(
        label="Usuário ativo",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, schools=None, roles=None, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.fields["role"].queryset = roles if roles is not None else Role.objects.all()
        if schools is not None:
            self.fields["school"].queryset = schools
        self.fields["school"].help_text = "Obrigatória para gestor, coordenador, AEE e professor."
        if instance:
            self.fields["username"].initial = instance.username
            self.fields["first_name"].initial = instance.first_name
            self.fields["last_name"].initial = instance.last_name
            self.fields["email"].initial = instance.email
            self.fields["is_active"].initial = instance.is_active
            profile = instance.profile
            if profile and profile.role_id:
                self.fields["role"].initial = profile.role_id
            if profile and profile.school_id:
                self.fields["school"].initial = profile.school_id
        else:
            self.fields["password"].required = True
            professor = Role.objects.filter(code=Role.Code.PROFESSOR).first()
            if professor:
                self.fields["role"].initial = professor.pk

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        qs = User.objects.filter(username=username)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este usuário já existe.")
        return username

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        school = cleaned.get("school")
        school_roles = {Role.Code.GESTOR, Role.Code.COORDENADOR, Role.Code.AEE, Role.Code.PROFESSOR}
        if role and role.code in school_roles and not school:
            self.add_error("school", "Este papel precisa de uma escola.")
        return cleaned

    def save(self) -> User:
        data = self.cleaned_data
        if self.instance:
            user = self.instance
            user.username = data["username"]
            user.first_name = data["first_name"]
            user.last_name = data.get("last_name") or ""
            user.email = data.get("email") or ""
            user.is_active = bool(data.get("is_active"))
            if data.get("password"):
                user.set_password(data["password"])
            user.save()
        else:
            user = User.objects.create_user(
                username=data["username"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data.get("last_name") or "",
                email=data.get("email") or "",
                is_active=bool(data.get("is_active", True)),
            )
        profile = user.userprofile
        profile.role = data["role"]
        profile.school = data.get("school")
        profile.display_name = f"{data['first_name']} {data.get('last_name') or ''}".strip()
        profile.save()
        return user


class TeacherClassroomForm(MitakaModelForm):
    class Meta:
        model = TeacherClassroom
        fields = ("teacher", "classroom", "is_primary")
        labels = {
            "teacher": "Professor / AEE",
            "classroom": "Turma",
            "is_primary": "Professor principal",
        }
        widgets = {
            "teacher": _select(),
            "classroom": _select(),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, teachers=None, classrooms=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teachers is not None:
            self.fields["teacher"].queryset = teachers
        if classrooms is not None:
            self.fields["classroom"].queryset = classrooms.select_related("school", "school_year")
