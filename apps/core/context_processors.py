from apps.core.permissions import nav_flags


def branding(request):
    return {
        "APP_NAME": "Mitaka Edu",
        "APP_TAGLINE": "Acompanhamento pedagógico — alfabetizar letrando (Currículo PE)",
        "MUNICIPALITY_NAME": "Jucati/PE",
        "CURRICULUM_FRAMEWORK": "Currículo de Pernambuco / BNCC",
    }


def navigation(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return {"nav": {}}
    return {"nav": nav_flags(user)}
