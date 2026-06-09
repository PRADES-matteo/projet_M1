from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from apps.costs import views as costs_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/register/", costs_views.register, name="register"),
    path("", RedirectView.as_view(url="/costs/", permanent=False), name="home"),
    path("costs/", include("apps.costs.urls")),
]
