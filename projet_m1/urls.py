from django.contrib import admin
from django.urls import include, path
from apps.costs import views as costs_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/register/", costs_views.register, name="register"),
    path("", include("apps.dashboard.urls")),
    path("costs/", include("apps.costs.urls")),
]
