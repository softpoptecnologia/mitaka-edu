"""Minimal JSON API for assessment autosave."""
from django.urls import path

from apps.assessments import views

urlpatterns = [
    path("sessoes/<int:session_id>/responder/", views.answer_item, name="api_answer"),
]
