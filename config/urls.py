"""Root URL routing."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import login_view, logout_view
from apps.adoption.views import PublicHomeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("", PublicHomeView.as_view(), name="home"),
    path("familia/", include("apps.adoption.urls_family")),
    path("professor/", include("apps.accounts.urls_teacher")),
    path("gestao/", include("apps.accounts.urls_management")),
    path("gestao/", include("apps.adoption.urls_adoption")),
    path("secretaria/", include("apps.analytics.urls_secretaria")),
    path("avaliacao/", include("apps.assessments.urls")),
    path("api/", include("apps.assessments.urls_api")),
    path("api/", include("apps.interventions.urls_api")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
