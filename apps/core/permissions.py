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
