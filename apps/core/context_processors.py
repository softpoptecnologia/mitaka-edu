from apps.core.permissions import nav_flags


def branding(request):
    return {
        "APP_NAME": "Mitaka Edu",
        "APP_TAGLINE": "Acompanhamento pedagógico — alfabetizar letrando (Currículo PE)",
        "MUNICIPALITY_NAME": "Jucati/PE",
        "CURRICULUM_FRAMEWORK": "Currículo de Pernambuco / BNCC",
    }


def navigation(request):
    try:
        user = getattr(request, "user", None)
        authenticated = bool(user and getattr(user, "is_authenticated", False))
        if not authenticated:
            return {"nav": {"ready": True}}
        flags = nav_flags(user)
        flags["ready"] = True
        return {"nav": flags}
    except Exception:
        return {"nav": {"ready": False}}
