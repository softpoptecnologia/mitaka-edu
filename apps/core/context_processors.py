from apps.core.permissions import nav_flags


def branding(request):
    return {
        "APP_NAME": "Mitaka Edu",
        "APP_TAGLINE": "Acompanhamento pedagógico — alfabetizar letrando (Currículo PE)",
        "MUNICIPALITY_NAME": "Jucati/PE",
        "CURRICULUM_FRAMEWORK": "Currículo de Pernambuco / BNCC",
    }


def navigation(request):
    from apps.core.permissions import is_authenticated_user

    try:
        user = getattr(request, "user", None)
        if not is_authenticated_user(user):
            return {"nav": {"ready": False}}
        flags = nav_flags(user)
        flags["ready"] = True
        return {"nav": flags}
    except Exception:
        return {"nav": {"ready": False}}
