from django.urls import path

from .views import scenario_detail, scenario_list

urlpatterns = [
    path("", scenario_list, name="scenario-list"),
    path("<int:pk>/", scenario_detail, name="scenario-detail"),
]
