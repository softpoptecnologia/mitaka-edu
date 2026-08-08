"""Role-based access helpers and mixins."""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


NETWORK_ROLES = ("SUPERADMIN", "SECRETARIA", "TECNICO")
MANAGEMENT_ROLES = ("SUPERADMIN", "SECRETARIA", "TECNICO", "GESTOR", "COORDENADOR", "AEE")
SCHOOL_ROLES = ("GESTOR", "COORDENADOR", "AEE")
SCHOOL_WRITE_ROLES = ("GESTOR", "COORDENADOR")
AEE_ROLES = ("AEE", "COORDENADOR", "GESTOR", "SUPERADMIN", "SECRETARIA", "TECNICO")
HARD_DELETE_ROLES = ("SUPERADMIN", "SECRETARIA")


def user_role_code(user) -> str | None:
    if not user or not user.is_authenticated:
        return None
    return user.role_code


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


def cadastro_flags(user, school=None) -> dict:
    return {
        "can_write_network": can_write_network(user),
        "can_write_school": can_write_school(user, school),
        "can_hard_delete": can_hard_delete(user),
    }


ROLE_NAV_LABELS = {
    "SUPERADMIN": "Superadmin",
    "SECRETARIA": "Secretaria",
    "TECNICO": "Técnico",
    "GESTOR": "Gestor",
    "COORDENADOR": "Coordenador",
    "PROFESSOR": "Professor",
    "AEE": "AEE",
}


def nav_flags(user) -> dict:
    """Which admin-sidebar items each role should see."""
    code = user_role_code(user)
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
