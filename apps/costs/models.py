from django.db import models
from decimal import Decimal
from django.utils.translation import gettext_lazy as _

class VariableCostCategory(models.TextChoices):
    MATERIAL = 'Material', 'Matériel'
    LABOR = 'Labor', 'Main-d’œuvre'
    OVERHEAD = 'Overhead', 'Frais généraux'

class CostScenario(models.Model):
    name = models.CharField(max_length=150)
    period = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    method = models.CharField(
        max_length=50,
        choices=[
            ("center_analysis", "Centres d'analyse"),
            ("direct_costing", "Direct costing"),
            ("direct_costing_advanced", "Direct costing évolué"),
        ],
        default="direct_costing",
    )
    input_mode = models.CharField(
        max_length=20,
        choices=[("ca_total", "Je fournis le CA"), ("pv_volume", "Je fournis PV et volumes")],
        default="pv_volume",
    )
    preset = models.CharField(
        max_length=20,
        choices=[("small_business", "Petite entreprise"), ("factory", "Usine"), ("distribution", "Distribution")],
        default="small_business",
    )
    ui_mode = models.CharField(
        max_length=10,
        choices=[("simple", "Simple"), ("expert", "Expert")],
        default="simple",
    )
    use_reciprocal_allocation = models.BooleanField(default=False)
    use_seasonality = models.BooleanField(default=False)
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
    is_product = models.BooleanField(default=False)

    def __str__(self):
        return self.label


class VariableCost(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=VariableCostCategory.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    scenario = models.ForeignKey(CostScenario, related_name='variable_costs', on_delete=models.CASCADE)

    def __str__(self):
        return self.name