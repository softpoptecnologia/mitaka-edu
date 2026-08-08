from django import template

register = template.Library()


@register.filter
def nav_on(nav, key):
    """Show a sidebar item. Fail open if nav flags were not loaded."""
    if not isinstance(nav, dict) or not nav.get("ready"):
        return True
    return bool(nav.get(key))
