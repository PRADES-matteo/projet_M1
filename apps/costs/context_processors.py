from .models import CostScenario

def sidebar_scenarios(request):
    if request.user.is_authenticated:
        scenarios = CostScenario.objects.filter(user=request.user).order_by("-created_at")
    else:
        scenarios = CostScenario.objects.none()

    return {
        "all_scenarios": scenarios
    }