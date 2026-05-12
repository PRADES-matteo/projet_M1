from django.shortcuts import render, redirect

from django.shortcuts import render, redirect
from .forms import CostScenarioForm, ProductForm, CostLineForm
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
    scenario = CostScenario.objects.prefetch_related("cost_lines", "cost_lines__center").get(pk=pk)
    cost_lines = scenario.cost_lines.all()
    return render(
        request,
        "costs/scenario_detail.html",
        {
            "scenario": scenario,
            "center_analysis": calculate_center_analysis(cost_lines),
            "direct_costing": calculate_direct_costing(cost_lines),
        },
    )


def create_scenario(request):
    if request.method == "POST":
        form = CostScenarioForm(request.POST)
        if form.is_valid():
            scenario = form.save()
            return redirect("add_product", scenario_id=scenario.id)
    else:
        form = CostScenarioForm()
    return render(request, "costs/create_scenario.html", {"form": form})


def add_product(request, scenario_id):
    scenario = CostScenario.objects.get(id=scenario_id)
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.scenario = scenario
            product.save()
            return redirect("add_cost_line", scenario_id=scenario.id, product_id=product.id)
    else:
        form = ProductForm()
    return render(request, "costs/add_product.html", {"form": form, "scenario": scenario})


def add_cost_line(request, scenario_id, product_id):
    scenario = CostScenario.objects.get(id=scenario_id)
    product = Product.objects.get(id=product_id)
    if request.method == "POST":
        form = CostLineForm(request.POST)
        if form.is_valid():
            cost_line = form.save(commit=False)
            cost_line.scenario = scenario
            cost_line.product = product
            cost_line.save()
            return redirect("add_cost_line", scenario_id=scenario.id, product_id=product.id)
    else:
        form = CostLineForm()
    return render(request, "costs/add_cost_line.html", {"form": form, "scenario": scenario, "product": product})


def calculate_results(request, scenario_id):
    scenario = CostScenario.objects.get(id=scenario_id)
    lines = scenario.cost_lines.all()
    if scenario.method == "direct_costing":
        result = calculate_direct_costing(lines)
    else:
        result = calculate_center_analysis(lines)

    return render(request, "costs/results.html", {"scenario": scenario, "result": result})
