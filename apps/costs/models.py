from django.db import models
from decimal import Decimal


class CostScenario(models.Model):
    name = models.CharField(max_length=150)
    period = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    method = models.CharField(
        max_length=50,
        choices=[("direct_costing", "Direct Costing"), ("center_analysis", "Center Analysis")],
        default="direct_costing",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    scenario = models.ForeignKey(CostScenario, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return self.name

    @property
    def total_revenue(self):
        return self.quantity * self.unit_price


class CostCenter(models.Model):
    scenario = models.ForeignKey(CostScenario, on_delete=models.CASCADE, related_name="cost_centers")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    is_auxiliary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.name}"


class CostLine(models.Model):
    scenario = models.ForeignKey(CostScenario, on_delete=models.CASCADE, related_name="cost_lines")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cost_lines", null=True, blank=True)
    label = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True, related_name="cost_lines")
    is_direct = models.BooleanField(default=False)

    def __str__(self):
        return self.label