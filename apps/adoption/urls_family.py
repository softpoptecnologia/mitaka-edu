from django.urls import path

from apps.adoption import views

app_name = "family"

urlpatterns = [
    path("", views.FamilyHomeView.as_view(), name="home"),
    path("crianca/<int:pk>/", views.FamilyChildView.as_view(), name="child"),
]
