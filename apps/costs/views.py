from django.shortcuts import render

from .models import CostScenario
from .services.center_analysis import calculate_center_analysis
from .services.direct_costing import calculate_direct_costing


def scenario_list(request):
    scenarios = CostScenario.objects.all().order_by("-created_at")
    return render(request, "costs/scenario_list.html", {"scenarios": scenarios})


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
