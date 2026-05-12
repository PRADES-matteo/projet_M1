from django.urls import path
from . import views

urlpatterns = [
    path("", views.scenario_list, name="scenario-list"),
    path("<int:pk>/", views.scenario_detail, name="scenario-detail"),
    path("<int:pk>/settings/", views.update_scenario_settings, name="scenario-settings"),
    path("scenario/create/", views.create_scenario, name="create_scenario"),
    path("scenario/<int:scenario_id>/product/add/", views.add_product, name="add_product"),
    path("scenario/<int:scenario_id>/product/<int:product_id>/cost-line/add/", views.add_cost_line, name="add_cost_line"),
    path("scenario/<int:scenario_id>/results/", views.calculate_results, name="calculate_results"),
]
