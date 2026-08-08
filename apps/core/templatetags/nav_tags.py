from django import template

from apps.core.permissions import is_authenticated_user, nav_flags

register = template.Library()


def _has_nav_flags(nav: dict) -> bool:
    return any(key in nav for key in ("role", "dashboard", "section_gestao", "section_relatorios"))


@register.filter
def nav_on(nav, key):
    """Show a sidebar item. Fail open if nav flags were not loaded."""
    if not isinstance(nav, dict) or not nav.get("ready") or not _has_nav_flags(nav):
        return True
    return bool(nav.get(key))


@register.simple_tag(takes_context=True)
def get_sidebar_nav(context):
    """Build sidebar flags from the same user rendered in the topbar."""
    request = context.get("request")
    user = getattr(request, "user", None) if request else None
    if not is_authenticated_user(user):
        user = context.get("user")
    if not is_authenticated_user(user):
        return {"ready": False}
    flags = nav_flags(user)
    flags["ready"] = True
    return flags
