from django.urls import path

from apps.adoption import views

app_name = "adoption"

urlpatterns = [
    path("implantacao/", views.ImplantationView.as_view(), name="implantation"),
    path("formacoes/", views.FormationListView.as_view(), name="formations"),
    path("uso/", views.UsageMonitoringView.as_view(), name="usage"),
]
