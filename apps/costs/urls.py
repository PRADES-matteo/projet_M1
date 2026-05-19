from django.urls import path
from . import views

urlpatterns = [
    path("", views.scenario_list, name="scenario-list"),
    path("scenario/compare/", views.compare_scenarios, name="compare_scenarios"),
    path("<int:pk>/", views.scenario_detail, name="scenario-detail"),
    path("<int:pk>/save/", views.save_scenario, name="scenario-save"),
    path("<int:pk>/versions/<int:version_id>/restore/", views.restore_scenario_version, name="scenario-version-restore"),
    path("<int:pk>/duplicate/", views.duplicate_scenario, name="scenario-duplicate"),
    path("scenario/create/", views.create_scenario, name="create_scenario"),
    path("scenario/<int:scenario_id>/product/add/", views.add_product, name="add_product"),
    path("scenario/<int:scenario_id>/product/<int:product_id>/edit/", views.edit_product, name="edit_product"),
    path("scenario/<int:scenario_id>/product/<int:product_id>/delete/", views.delete_product, name="delete_product"),
    path("scenario/<int:scenario_id>/product/<int:product_id>/cost-line/add/", views.add_cost_line, name="add_cost_line"),
    path("scenario/<int:scenario_id>/results/", views.calculate_results, name="calculate_results"),
    path('scenario/<int:scenario_id>/variable-cost/add/', views.VariableCostCreateView.as_view(), name='add_variable_cost'),
    path('variable-cost/<int:pk>/edit/', views.VariableCostUpdateView.as_view(), name='edit_variable_cost'),
    path('variable-cost/<int:pk>/delete/', views.VariableCostDeleteView.as_view(), name='delete_variable_cost'),
    path('scenario/<int:scenario_id>/fixed-cost/add/', views.FixedCostCreateView.as_view(), name='add_fixed_cost'),
    path('fixed-cost/<int:pk>/edit/', views.FixedCostUpdateView.as_view(), name='edit_fixed_cost'),
    path('fixed-cost/<int:pk>/delete/', views.FixedCostDeleteView.as_view(), name='delete_fixed_cost'),
    path('scenario/<int:scenario_id>/seasonality/', views.edit_seasonality, name='edit_seasonality'),
]
