from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views import View

from apps.accounts.models import Role
from apps.core.permissions import user_role_code
from apps.core.services.audit import log_action

DEMO_PROFILES = [
    {
        "username": "secretaria",
        "password": "demo1234",
        "label": "Secretaria",
        "description": "Visão da rede municipal",
    },
    {
        "username": "professora",
        "password": "demo1234",
        "label": "Professora",
        "description": "Turmas e sondagens",
    },
    {
        "username": "gestor",
        "password": "demo1234",
        "label": "Gestor",
        "description": "Gestão da escola",
    },
    {
        "username": "coordenador",
        "password": "demo1234",
        "label": "Coordenador",
        "description": "Acompanhamento pedagógico",
    },
    {
        "username": "aee",
        "password": "demo1234",
        "label": "AEE",
        "description": "Apoio e acessibilidade",
    },
    {
        "username": "tecnico",
        "password": "demo1234",
        "label": "Técnico",
        "description": "Indicadores e matriz",
    },
    {
        "username": "admin",
        "password": "demo1234",
        "label": "Admin",
        "description": "Administração completa",
    },
]


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            log_action(actor=user, action="login", object_type="User", object_id=user.pk, message="Entrada no sistema")
            return redirect("home")
        error = "Usuário ou senha inválidos."
    return render(
        request,
        "registration/login.html",
        {
            "error": error,
            "demo_profiles": DEMO_PROFILES if settings.SHOW_DEMO_PROFILES else [],
            "show_demo_profiles": settings.SHOW_DEMO_PROFILES,
        },
    )


def logout_view(request):
    logout(request)
    return redirect("login")


class HomeRedirectView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")
        code = user_role_code(request.user)
        if code in (Role.Code.PROFESSOR, Role.Code.AEE):
            return redirect("teacher:home")
        if code in (Role.Code.SECRETARIA, Role.Code.TECNICO, Role.Code.SUPERADMIN):
            return redirect("secretaria:dashboard")
        return redirect("management:dashboard")
