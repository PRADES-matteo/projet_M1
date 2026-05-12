from decimal import Decimal

from django.shortcuts import render, redirect
from .forms import CostScenarioForm, ProductForm, CostLineForm, ScenarioSettingsForm
from .models import CostScenario, Product, CostLine
from .services.direct_costing import calculate_direct_costing
from .services.center_analysis import calculate_center_analysis



def scenario_list(request):
    if request.method == "POST":
        form = CostScenarioForm(request.POST)
        if form.is_valid():
            scenario = form.save()
            return redirect("scenario-detail", pk=scenario.pk)
    else:
        form = CostScenarioForm()

    scenarios = CostScenario.objects.all().order_by("-created_at")
    return render(request, "costs/scenario_list.html", {"scenarios": scenarios, "form": form})


def scenario_detail(request, pk):
    scenario = CostScenario.objects.prefetch_related("products", "cost_lines", "cost_lines__center").get(pk=pk)
    cost_lines = scenario.cost_lines.all()

    summary_rows = []
    total_revenue = Decimal("0.00")
    total_variable = Decimal("0.00")
    total_fixed = Decimal("0.00")

    for product in scenario.products.all():
        quantity = Decimal(product.quantity)
        unit_price = Decimal(product.unit_price)
        revenue = quantity * unit_price
        variable = Decimal("0.00")
        fixed = Decimal("0.00")

        for line in product.cost_lines.all():
            if line.is_direct:
                variable += line.amount
            else:
                fixed += line.amount

        contribution = revenue - variable
        result = contribution - fixed
        variable_unit_cost = variable / quantity if quantity else Decimal("0.00")
        summary_rows.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": unit_price,
                "variable_unit_cost": variable_unit_cost,
                "revenue": revenue,
                "variable": variable,
                "fixed": fixed,
                "contribution": contribution,
                "result": result,
            }
        )
        total_revenue += revenue
        total_variable += variable
        total_fixed += fixed

    total_contribution = total_revenue - total_variable
    total_result = total_contribution - total_fixed

    return render(
        request,
        "costs/scenario_detail.html",
        {
            "scenario": scenario,
            "settings_form": ScenarioSettingsForm(instance=scenario),
            "center_analysis": calculate_center_analysis(cost_lines),
            "direct_costing": calculate_direct_costing(cost_lines),
            "summary_rows": summary_rows,
            "summary_totals": {
                "revenue": total_revenue,
                "variable": total_variable,
                "fixed": total_fixed,
                "contribution": total_contribution,
                "result": total_result,
            },
        },
    )


def update_scenario_settings(request, pk):
    scenario = CostScenario.objects.get(pk=pk)
    if request.method == "POST":
        form = ScenarioSettingsForm(request.POST, instance=scenario)
        if form.is_valid():
            form.save()
    return redirect("scenario-detail", pk=pk)


def create_scenario(request):
    if request.method == "POST":
        form = CostScenarioForm(request.POST)
        if form.is_valid():
            scenario = form.save()
            return redirect("scenario-detail", pk=scenario.id)
    else:
        form = CostScenarioForm()
    return render(request, "costs/create_scenario.html", {"form": form})


def add_product(request, scenario_id):
    scenario = CostScenario.objects.get(id=scenario_id)
    if request.method == "POST":
        form = ProductForm(request.POST, scenario=scenario)
        if form.is_valid():
            product = form.save(commit=False)
            product.scenario = scenario

            entry_mode = form.cleaned_data.get("entry_mode")
            if entry_mode == "ca_total":
                quantity = Decimal(form.cleaned_data["quantity"])
                revenue_total = Decimal(form.cleaned_data["revenue_total"])
                product.unit_price = (revenue_total / quantity) if quantity else Decimal("0.00")

            product.save()
            return redirect("add_cost_line", scenario_id=scenario.id, product_id=product.id)
    else:
        form = ProductForm(scenario=scenario)
    return render(request, "costs/add_product.html", {"form": form, "scenario": scenario})


def add_cost_line(request, scenario_id, product_id):
    scenario = CostScenario.objects.get(id=scenario_id)
    product = Product.objects.get(id=product_id)
    if request.method == "POST":
        form = CostLineForm(request.POST, scenario=scenario)
        if form.is_valid():
            cost_line = form.save(commit=False)
            cost_line.scenario = scenario
            cost_line.product = product
            cost_line.save()
            return redirect("add_cost_line", scenario_id=scenario.id, product_id=product.id)
    else:
        form = CostLineForm(scenario=scenario)
    return render(request, "costs/add_cost_line.html", {"form": form, "scenario": scenario, "product": product})


def calculate_results(request, scenario_id):
    scenario = CostScenario.objects.get(id=scenario_id)
    lines = scenario.cost_lines.all()
    if scenario.method == "direct_costing":
        result = calculate_direct_costing(lines)
    else:
        result = calculate_center_analysis(lines)

    return render(request, "costs/results.html", {"scenario": scenario, "result": result})
