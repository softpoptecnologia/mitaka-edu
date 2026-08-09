from django.urls import path

from apps.accounts import api

urlpatterns = [
    path("auth/login/", api.TeacherAppLoginAPIView.as_view(), name="api_teacher_login"),
    path("auth/logout/", api.TeacherAppLogoutAPIView.as_view(), name="api_teacher_logout"),
    path("professor/bootstrap/", api.TeacherBootstrapAPIView.as_view(), name="api_teacher_bootstrap"),
    path("professor/atividades-ludicas/", api.LudicActivityAPIView.as_view(), name="api_teacher_ludic"),
]
