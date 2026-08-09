"""Auth and bootstrap JSON for the Flutter teacher app."""
from __future__ import annotations

from django.contrib.auth import authenticate
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services.teacher_app import bootstrap_payload, teacher_payload
from apps.core.permissions import can_use_teacher_app
from apps.core.services.audit import log_action
from apps.interventions.api import IsTeacherPortalUser
from apps.assessments.services.ludic import LudicActivityError, record_ludic_activity


class TeacherAppLoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response({"detail": "Informe usuário e senha."}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            return Response({"detail": "Usuário ou senha inválidos."}, status=status.HTTP_400_BAD_REQUEST)
        if not can_use_teacher_app(user):
            return Response(
                {"detail": "Este app é só para a professora. AEE, gestão e família usam a web."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            token, _ = Token.objects.get_or_create(user=user)
        except (OperationalError, ProgrammingError):
            return Response(
                {"detail": "Falta migrar o banco do app (authtoken). Rode: python manage.py migrate"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        log_action(
            actor=user,
            action="login",
            object_type="User",
            object_id=user.pk,
            message="Entrada pelo app do professor",
        )
        payload = bootstrap_payload(user)
        payload["token"] = token.key
        payload["teacher"] = teacher_payload(user)
        return Response(payload)


class TeacherAppLogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"ok": True})


class TeacherBootstrapAPIView(APIView):
    permission_classes = [IsTeacherPortalUser]

    def get(self, request):
        return Response(bootstrap_payload(request.user))


class LudicActivityAPIView(APIView):
    permission_classes = [IsTeacherPortalUser]

    def post(self, request):
        try:
            student_id = int(request.data.get("student_id"))
        except (TypeError, ValueError):
            return Response({"detail": "Informe o estudante."}, status=status.HTTP_400_BAD_REQUEST)
        enrollment_raw = request.data.get("enrollment_id")
        try:
            enrollment_id = int(enrollment_raw) if enrollment_raw not in (None, "") else None
        except (TypeError, ValueError):
            enrollment_id = None
        try:
            result = record_ludic_activity(
                user=request.user,
                student_id=student_id,
                enrollment_id=enrollment_id,
                activity_id=(request.data.get("activity_id") or "").strip() or "atividade",
                activity_title=(request.data.get("activity_title") or "").strip() or "Atividade lúdica",
                skill_code=(request.data.get("skill_code") or "").strip(),
                mode=(request.data.get("mode") or "survey").strip() or "survey",
                label=(request.data.get("label") or "").strip(),
                score=int(request.data.get("score") or 0),
                total=int(request.data.get("total") or 0),
                needs_attention=request.data.get("needs_attention"),
                observation=(request.data.get("observation") or "").strip(),
                answers=request.data.get("answers") or [],
                observational=bool(request.data.get("observational")),
            )
        except LudicActivityError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)
