from django.urls import path

from apps.assessments import views

app_name = "assessment"

urlpatterns = [
    path(
        "preparar/<int:enrollment_id>/<int:instrument_id>/",
        views.PreviewAdaptedAssessmentView.as_view(),
        name="preview",
    ),
    path(
        "imprimir/<int:enrollment_id>/<int:instrument_id>/",
        views.PrintAccessibleAssessmentView.as_view(),
        name="print",
    ),
    path("iniciar/<int:enrollment_id>/<int:instrument_id>/", views.StartAssessmentView.as_view(), name="start"),
    path("sessao/<int:session_id>/", views.PlayAssessmentView.as_view(), name="play"),
    path("sessao/<int:session_id>/responder/", views.answer_item, name="answer"),
    path("sessao/<int:session_id>/concluir/", views.finish_session, name="finish"),
]
