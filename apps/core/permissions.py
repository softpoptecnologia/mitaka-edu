"""Role-based access helpers and mixins."""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


NETWORK_ROLES = ("SUPERADMIN", "SECRETARIA", "TECNICO")
MANAGEMENT_ROLES = ("SUPERADMIN", "SECRETARIA", "TECNICO", "GESTOR", "COORDENADOR", "AEE")
SCHOOL_ROLES = ("GESTOR", "COORDENADOR", "AEE")
SCHOOL_WRITE_ROLES = ("GESTOR", "COORDENADOR")
AEE_ROLES = ("AEE", "COORDENADOR", "GESTOR", "SUPERADMIN", "SECRETARIA", "TECNICO")
HARD_DELETE_ROLES = ("SUPERADMIN", "SECRETARIA")
TEACHER_APP_ROLES = ("PROFESSOR",)

ROLE_NAV_LABELS = {
    "SUPERADMIN": "Superadmin",
    "SECRETARIA": "Secretaria",
    "TECNICO": "Técnico",
    "GESTOR": "Gestor",
    "COORDENADOR": "Coordenador",
    "PROFESSOR": "Professor",
    "AEE": "AEE",
    "FAMILIA": "Família",
}

ROLE_ALIASES = {
    "GESTOR ESCOLAR": "GESTOR",
    "GESTORA": "GESTOR",
    "DIRETOR": "GESTOR",
    "DIRETORA": "GESTOR",
    "COORDENADOR PEDAGOGICO": "COORDENADOR",
    "COORDENADORA": "COORDENADOR",
    "PROFESSORA": "PROFESSOR",
    "TECNICO PEDAGOGICO": "TECNICO",
    "TECNICA": "TECNICO",
}


def is_authenticated_user(user) -> bool:
    if user is None:
        return False
    value = getattr(user, "is_authenticated", False)
    if callable(value):
        value = value()
    return bool(value)


def normalize_role_code(code) -> str | None:
    if not code:
        return None
    raw = str(code).strip().upper()
    collapsed = " ".join(raw.replace("-", " ").replace("_", " ").split())
    underscored = collapsed.replace(" ", "_")
    known = set(ROLE_NAV_LABELS) | set(NETWORK_ROLES) | set(MANAGEMENT_ROLES) | {"PROFESSOR", "FAMILIA"}
    if underscored in known:
        return underscored
    return ROLE_ALIASES.get(collapsed) or ROLE_ALIASES.get(raw)


def user_role_code(user) -> str | None:
    if not is_authenticated_user(user):
        return None
    code = getattr(user, "role_code", None)
    normalized = normalize_role_code(code)
    if normalized:
        return normalized
    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "school_id", None):
        return "GESTOR"
    return None


def require_roles(user, *codes: str):
    if not user.is_authenticated or user_role_code(user) not in codes:
        raise PermissionDenied("Permissão insuficiente.")


def can_write_network(user) -> bool:
    return user_role_code(user) in NETWORK_ROLES


def can_write_school(user, school=None) -> bool:
    code = user_role_code(user)
    if code in NETWORK_ROLES:
        return True
    if code not in SCHOOL_WRITE_ROLES:
        return False
    if school is None:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.school_id == getattr(school, "pk", None))


def can_hard_delete(user) -> bool:
    return user_role_code(user) in HARD_DELETE_ROLES


def can_use_teacher_app(user) -> bool:
    """Flutter tablet app: professora only. AEE/gestão/família use the web."""
    return user_role_code(user) in TEACHER_APP_ROLES


def cadastro_flags(user, school=None) -> dict:
    return {
        "can_write_network": can_write_network(user),
        "can_write_school": can_write_school(user, school),
        "can_hard_delete": can_hard_delete(user),
    }


def _nav_all_visible(**extra) -> dict:
    flags = {
        "dashboard": True,
        "municipality": True,
        "schools": True,
        "classrooms": True,
        "students": True,
        "enrollments": True,
        "import_students": True,
        "teachers": True,
        "school_years": True,
        "matrix": True,
        "dimensions": True,
        "alignment": True,
        "instruments": True,
        "templates": True,
        "indicators": True,
        "interventions": True,
        "secretaria": True,
        "reports": True,
        "report_school": True,
        "report_network": True,
        "teacher_portal": True,
        "implantation": True,
        "formations": True,
        "usage": True,
        "section_gestao": True,
        "section_curriculo": True,
        "section_secretaria": True,
        "section_relatorios": True,
    }
    flags.update(extra)
    return flags


def nav_flags(user) -> dict:
    """Which admin-sidebar items each role should see."""
    code = user_role_code(user)
    if not code:
        return _nav_all_visible(role=None, role_label="")

    network = code in NETWORK_ROLES
    school_write = code in SCHOOL_WRITE_ROLES
    school_scope = code in SCHOOL_ROLES
    aee = code == "AEE"
    professor = code == "PROFESSOR"
    management = code in MANAGEMENT_ROLES

    municipality = network
    schools = network or school_scope
    classrooms = network or school_scope
    students = network or school_scope
    enrollments = network or school_write
    import_students = network or school_write
    teachers = network or school_write
    school_years = network
    matrix = network
    dimensions = network
    alignment = network or school_write
    instruments = network
    templates = network or school_scope
    indicators = network or school_scope
    interventions = network or school_scope
    secretaria = network
    reports = professor or management
    report_school = network or school_scope
    report_network = network
    teacher_portal = professor or aee or school_write
    implantation = network
    formations = network or school_scope
    usage = network
    dashboard = management

    section_gestao = any(
        [
            dashboard,
            municipality,
            schools,
            classrooms,
            students,
            enrollments,
            import_students,
            teachers,
            school_years,
        ]
    )
    section_curriculo = any(
        [matrix, dimensions, alignment, instruments, templates, indicators, interventions]
    )

    return {
        "role": code,
        "role_label": ROLE_NAV_LABELS.get(code or "", ""),
        "dashboard": dashboard,
        "municipality": municipality,
        "schools": schools,
        "classrooms": classrooms,
        "students": students,
        "enrollments": enrollments,
        "import_students": import_students,
        "teachers": teachers,
        "school_years": school_years,
        "matrix": matrix,
        "dimensions": dimensions,
        "alignment": alignment,
        "instruments": instruments,
        "templates": templates,
        "indicators": indicators,
        "interventions": interventions,
        "secretaria": secretaria,
        "reports": reports,
        "report_school": report_school,
        "report_network": report_network,
        "teacher_portal": teacher_portal,
        "implantation": implantation,
        "formations": formations,
        "usage": usage,
        "section_gestao": section_gestao,
        "section_curriculo": section_curriculo,
        "section_secretaria": secretaria,
        "section_relatorios": reports,
    }


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles: tuple[str, ...] = ()

    def test_func(self) -> bool:
        if not self.allowed_roles:
            return self.request.user.is_authenticated
        code = user_role_code(self.request.user)
        return code in self.allowed_roles


class ManagementRequiredMixin(RoleRequiredMixin):
    allowed_roles = MANAGEMENT_ROLES


class TeacherRequiredMixin(RoleRequiredMixin):
    allowed_roles = ("PROFESSOR",) + MANAGEMENT_ROLES


class AEERequiredMixin(RoleRequiredMixin):
    allowed_roles = AEE_ROLES


class NetworkRequiredMixin(RoleRequiredMixin):
    allowed_roles = NETWORK_ROLES


class FamilyRequiredMixin(RoleRequiredMixin):
    allowed_roles = ("FAMILIA",)
