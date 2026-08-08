"""Least-privilege checks for accessibility and support data."""
from __future__ import annotations

from apps.accounts.models import Role
from apps.accounts.selectors import user_can_access_student
from apps.core.permissions import user_role_code

# Can see functional resources needed for teaching
VIEW_ROLES = (
    Role.Code.SUPERADMIN,
    Role.Code.SECRETARIA,
    Role.Code.TECNICO,
    Role.Code.GESTOR,
    Role.Code.COORDENADOR,
    Role.Code.PROFESSOR,
    Role.Code.AEE,
)

# Can edit accessibility profile / support plan (not professor by default)
CHANGE_ROLES = (
    Role.Code.SUPERADMIN,
    Role.Code.SECRETARIA,
    Role.Code.TECNICO,
    Role.Code.GESTOR,
    Role.Code.COORDENADOR,
    Role.Code.AEE,
)

AEE_ROLES = (Role.Code.AEE,) + CHANGE_ROLES


def can_view_accessibility_profile(user, student) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user_role_code(user) not in VIEW_ROLES:
        return False
    return user_can_access_student(user, student)


def can_change_accessibility_profile(user, student) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user_role_code(user) not in CHANGE_ROLES:
        return False
    return user_can_access_student(user, student)


def can_manage_support_plan(user, student) -> bool:
    return can_change_accessibility_profile(user, student)


def active_resource_labels_for_teacher(student) -> list[str]:
    """What the teacher should primarily see: needed resources, not clinical data."""
    profile = getattr(student, "accessibility_profile", None)
    if profile is None or not profile.is_active:
        return []
    return list(profile.active_features().values_list("name", flat=True))
