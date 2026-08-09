from django.urls import path

from apps.accounts import views_teacher as views
from apps.accessibility import views as accessibility_views
from apps.interventions import views as intervention_views
from apps.interventions import views_teacher as journey_views
from apps.planning import views_teacher as planning_views

app_name = "teacher"

urlpatterns = [
    path("", views.TeacherHomeView.as_view(), name="home"),
    path("hoje/", views.TeacherHomeView.as_view(), name="today"),
    path("turmas/", views.TeacherClassroomListView.as_view(), name="classrooms"),
    path("turmas/<int:pk>/", views.TeacherClassroomDetailView.as_view(), name="classroom"),
    path("turmas/<int:pk>/planejamento/", views.ClassroomPlanningView.as_view(), name="planning"),
    path("turmas/<int:pk>/planejar-aula/", planning_views.LessonPlannerView.as_view(), name="lesson_plan"),
    path(
        "turmas/<int:classroom_id>/grupos/<int:skill_id>/",
        journey_views.SuggestedGroupView.as_view(),
        name="suggested_group",
    ),
    path("estudantes/<int:pk>/", views.StudentProfileView.as_view(), name="student"),
    path(
        "estudantes/<int:pk>/acessibilidade/",
        views.UpdateAccessibilityProfileView.as_view(),
        name="accessibility_update",
    ),
    path("estudantes/<int:pk>/plano-apoio/novo/", accessibility_views.SupportPlanCreateView.as_view(), name="support_plan_create"),
    path("planos-apoio/<int:pk>/editar/", accessibility_views.SupportPlanUpdateView.as_view(), name="support_plan_update"),
    path("planos-apoio/<int:pk>/estrategia/", accessibility_views.SupportStrategyCreateView.as_view(), name="support_strategy_create"),
    path("estudantes/<int:pk>/evidencias/nova/", views.EvidenceCreateView.as_view(), name="evidence_create"),
    path("estudantes/<int:pk>/intervencoes/nova/", views.InterventionCreateView.as_view(), name="intervention_create"),
    path(
        "estudantes/<int:pk>/intervencoes/aceitar/<int:template_id>/",
        views.AcceptInterventionTemplateView.as_view(),
        name="intervention_accept",
    ),
    path("intervencoes/<int:pk>/status/", intervention_views.StudentInterventionStatusView.as_view(), name="intervention_status"),
    path("intervencoes/<int:pk>/registrar/", journey_views.QuickFollowupView.as_view(), name="quick_followup"),
    path(
        "intervencoes-aluno/<int:pk>/registrar/",
        journey_views.StudentQuickFollowupView.as_view(),
        name="quick_followup_student",
    ),
    path("acoes/ignorar/", journey_views.DismissActionView.as_view(), name="dismiss_action"),
    path("sessoes/<int:pk>/resultado/", views.SessionResultView.as_view(), name="session_result"),
]
