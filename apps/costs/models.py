from django.db import models


class CostScenario(models.Model):
    name = models.CharField(max_length=150)
    period = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CostCenter(models.Model):
    scenario = models.ForeignKey(CostScenario, on_delete=models.CASCADE, related_name="cost_centers")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    is_auxiliary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.name}"


class CostLine(models.Model):
    scenario = models.ForeignKey(CostScenario, on_delete=models.CASCADE, related_name="cost_lines")
    label = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True, related_name="cost_lines")
    is_direct = models.BooleanField(default=False)

    def __str__(self):
        return self.label
