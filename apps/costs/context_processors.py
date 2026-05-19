from .models import CostScenario

def sidebar_scenarios(request):
    return {
        "all_scenarios": CostScenario.objects.all().order_by("-created_at")
    }