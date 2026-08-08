from django.urls import path

from apps.analytics import views_secretaria as views
from apps.curriculum.views import CurriculumAlignmentView

app_name = "secretaria"

urlpatterns = [
    path("", views.SecretariaDashboardView.as_view(), name="dashboard"),
    path("comparacao/", views.SchoolCompareView.as_view(), name="compare"),
    path("necessidades/", views.PedagogicalNeedsView.as_view(), name="needs"),
    path("navegacao/", views.DrillDownView.as_view(), name="drilldown"),
    path("alinhamento-curricular/", CurriculumAlignmentView.as_view(), name="curriculum_alignment"),
]
