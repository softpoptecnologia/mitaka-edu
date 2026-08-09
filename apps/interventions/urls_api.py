from django.urls import path

from apps.interventions import api

urlpatterns = [
    path("professor/hoje/", api.TeacherTodayAPIView.as_view(), name="api_teacher_today"),
    path("professor/turmas/<int:classroom_id>/resumo/", api.ClassroomSummaryAPIView.as_view(), name="api_teacher_classroom_summary"),
    path(
        "professor/turmas/<int:classroom_id>/grupos-sugeridos/",
        api.SuggestedGroupsAPIView.as_view(),
        name="api_teacher_suggested_groups",
    ),
    path(
        "professor/turmas/<int:classroom_id>/plano-sugerido/",
        api.SuggestedLessonAPIView.as_view(),
        name="api_teacher_suggested_lesson",
    ),
    path(
        "professor/intervencoes/<int:intervention_id>/registrar-lote/",
        api.BatchFollowupAPIView.as_view(),
        name="api_teacher_batch_followup",
    ),
    path("professor/reavaliacoes/", api.ReassessmentAPIView.as_view(), name="api_teacher_reassessments"),
]
