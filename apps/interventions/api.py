"""Authenticated teacher API for the future Flutter app."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.selectors import user_can_access_classroom
from apps.core.permissions import MANAGEMENT_ROLES, user_role_code
from apps.interventions.models import ClassroomIntervention
from apps.interventions.services.apply_group import apply_suggested_group
from apps.interventions.services.grouping import suggest_group_for_skill, suggest_groups
from apps.interventions.services.quick_followup import (
    followup_targets_for_classroom_intervention,
    record_batch_followup,
)
from apps.interventions.services.reassessment import suggestions_for_snapshot
from apps.interventions.services.snapshot import load_classroom_snapshot, load_snapshots_for_user
from apps.interventions.services.teacher_actions import build_teacher_action_queue
from apps.planning.services.lesson_builder import accept_lesson_proposal, build_lesson_proposal, normalize_duration
from apps.schools.models import Classroom


class IsTeacherPortalUser(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        code = user_role_code(request.user)
        return code == "PROFESSOR" or code in MANAGEMENT_ROLES


def _forbidden():
    return Response({"detail": "Você não tem acesso a este recurso."}, status=403)


def _classroom_or_403(request, classroom_id):
    try:
        classroom = Classroom.objects.select_related("school", "school_year").get(pk=classroom_id)
    except Classroom.DoesNotExist:
        return None, Response({"detail": "Turma não encontrada."}, status=404)
    if not user_can_access_classroom(request.user, classroom):
        return None, _forbidden()
    return classroom, None


class TeacherTodayAPIView(APIView):
    permission_classes = [IsTeacherPortalUser]

    def get(self, request):
        queue = build_teacher_action_queue(request.user)
        snapshots = queue.snapshots
        return Response(
            {
                "greeting": request.user.profile.greeting_name if getattr(request.user, "profile", None) else request.user.get_full_name(),
                "count": queue.count,
                "actions": [a.to_dict() for a in queue.actions],
                "classrooms": [
                    {
                        "id": snap.classroom.pk,
                        "name": snap.classroom.name,
                        **snap.summary_counts(),
                    }
                    for snap in snapshots
                ],
            }
        )


class ClassroomSummaryAPIView(APIView):
    permission_classes = [IsTeacherPortalUser]

    def get(self, request, classroom_id):
        classroom, error = _classroom_or_403(request, classroom_id)
        if error:
            return error
        snapshot = load_classroom_snapshot(classroom)
        return Response(
            {
                "classroom_id": classroom.pk,
                "name": classroom.name,
                "summary": snapshot.summary_counts(),
                "needs": [g.to_dict() for g in suggest_groups(snapshot) if g.kind != "consolidation"],
                "students": [
                    {
                        "id": r.student_id,
                        "name": r.student.full_name,
                        "needs_attention": r.needs_attention,
                        "pending": not r.has_completed_session,
                        "feature_names": r.feature_names,
                    }
                    for r in snapshot.records
                ],
            }
        )


class SuggestedGroupsAPIView(APIView):
    permission_classes = [IsTeacherPortalUser]

    def get(self, request, classroom_id):
        classroom, error = _classroom_or_403(request, classroom_id)
        if error:
            return error
        snapshot = load_classroom_snapshot(classroom)
        return Response(
            {
                "classroom_id": classroom.pk,
                "groups": [g.to_dict() for g in suggest_groups(snapshot, include_consolidation=True)],
            }
        )


class SuggestedLessonAPIView(APIView):
    permission_classes = [IsTeacherPortalUser]

    def post(self, request, classroom_id):
        classroom, error = _classroom_or_403(request, classroom_id)
        if error:
            return error
        duration = normalize_duration(request.data.get("duration") or request.data.get("duracao") or 45)
        snapshot = load_classroom_snapshot(classroom)
        proposal = build_lesson_proposal(snapshot, duration_minutes=duration)
        if request.data.get("accept"):
            plan = accept_lesson_proposal(
                user=request.user,
                snapshot=snapshot,
                proposal=proposal,
                adjusted=bool(request.data.get("adjusted")),
            )
            return Response({"accepted": True, "plan_id": plan.pk, "proposal": proposal.to_dict()}, status=201)
        return Response({"proposal": proposal.to_dict()})


class BatchFollowupAPIView(APIView):
    permission_classes = [IsTeacherPortalUser]

    def post(self, request, intervention_id):
        try:
            intervention = ClassroomIntervention.objects.select_related("classroom", "skill", "template").get(pk=intervention_id)
        except ClassroomIntervention.DoesNotExist:
            return Response({"detail": "Atividade não encontrada."}, status=404)
        if not user_can_access_classroom(request.user, intervention.classroom):
            return _forbidden()
        targets = followup_targets_for_classroom_intervention(intervention)
        raw_results = request.data.get("results") or {}
        mapped = {}
        for target in targets:
            value = raw_results.get(str(target.pk)) or raw_results.get(str(target.student_id))
            if value:
                mapped[target.pk] = value
        if not mapped:
            return Response({"detail": "Informe o resultado de pelo menos um estudante."}, status=400)
        batch = record_batch_followup(
            user=request.user,
            interventions=targets,
            results=mapped,
            general_notes=(request.data.get("notes") or request.data.get("general_notes") or "").strip(),
            classroom_intervention=intervention,
        )
        return Response(
            {
                "saved": len(batch.entries),
                "results": [
                    {
                        "student_id": e.student_intervention.student_id,
                        "result": e.result,
                        "evidence_id": e.evidence.pk if e.evidence else None,
                    }
                    for e in batch.entries
                ],
            }
        )


class ReassessmentAPIView(APIView):
    permission_classes = [IsTeacherPortalUser]

    def get(self, request):
        snapshots = load_snapshots_for_user(request.user)
        items = []
        for snapshot in snapshots:
            for suggestion in suggestions_for_snapshot(snapshot):
                payload = {
                    "classroom_id": suggestion.classroom_id,
                    "student_id": suggestion.student_id,
                    "student_name": suggestion.student_name,
                    "skill_id": suggestion.skill_id,
                    "skill_name": suggestion.skill_name,
                    "reason": suggestion.reason,
                    "days_since": suggestion.days_since,
                    "instrument_id": suggestion.instrument_id,
                }
                items.append(payload)
        return Response({"count": len(items), "items": items})
