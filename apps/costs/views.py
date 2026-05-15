from decimal import Decimal
from django.urls import reverse

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, UpdateView, DeleteView
from django.db.models import Sum
import calendar
from .forms import CostScenarioForm, ProductForm, CostLineForm, VariableCostForm, FixedCostForm
from .models import CostScenario, Product, CostLine, VariableCost, FixedCost
from .services.direct_costing import calculate_direct_costing
from .services.center_analysis import calculate_center_analysis


def _decimal(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def build_automatic_results(scenario):
    products = list(scenario.products.prefetch_related("cost_lines"))
    variable_costs = list(scenario.variable_costs.select_related("product"))
    fixed_costs = list(scenario.fixed_costs.select_related("product"))

    total_revenue = Decimal("0.00")
    total_variable_costs = Decimal("0.00")
    total_fixed_costs = Decimal("0.00")
    fixed_specific_costs = Decimal("0.00")

    for product in products:
        total_revenue += _decimal(product.total_revenue)

    for cost in variable_costs:
        total_variable_costs += _decimal(cost.amount)

    for cost in fixed_costs:
        amount = _decimal(cost.amount)
        total_fixed_costs += amount
        if not cost.is_common:
            fixed_specific_costs += amount

    mcv = total_revenue - total_variable_costs
    taux_marge = (mcv / total_revenue * Decimal("100.00")) if total_revenue else Decimal("0.00")
    seuil_rentabilite = (total_fixed_costs / (mcv / total_revenue)) if total_revenue and mcv > 0 else Decimal("0.00")
    point_mort = ((seuil_rentabilite / total_revenue) * Decimal("365.00")) if total_revenue and seuil_rentabilite else Decimal("0.00")
    marge_securite = total_revenue - seuil_rentabilite
    indice_securite = ((marge_securite / total_revenue) * Decimal("100.00")) if total_revenue else Decimal("0.00")
    resultat = mcv - total_fixed_costs
    levier_operationnel = (mcv / resultat) if resultat else Decimal("0.00")

    marge_specifique = mcv - fixed_specific_costs
    seuil_rentabilite_specifique = (fixed_specific_costs / (mcv / total_revenue)) if total_revenue and mcv > 0 else Decimal("0.00")

    return {
        "total_revenue": total_revenue,
        "total_variable_costs": total_variable_costs,
        "total_fixed_costs": total_fixed_costs,
        "fixed_specific_costs": fixed_specific_costs,
        "mcv": mcv,
        "taux_marge": taux_marge,
        "seuil_rentabilite": seuil_rentabilite,
        "point_mort": point_mort,
        "indice_securite": indice_securite,
        "marge_securite": marge_securite,
        "levier_operationnel": levier_operationnel,
        "marge_specifique": marge_specifique,
        "seuil_rentabilite_specifique": seuil_rentabilite_specifique,
        "resultat": resultat,
        "has_chart_data": any(value != 0 for value in [total_revenue, total_variable_costs, total_fixed_costs]),
    }



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

    variable_costs_total = scenario.variable_costs.aggregate(total=Sum('amount'))['total'] or 0
    fixed_costs_total = scenario.fixed_costs.aggregate(total=Sum('amount'))['total'] or 0

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

    # Seasonality: ensure entries exist for months 1..12
    from .models import SeasonalityEntry
    existing = {e.month: e for e in scenario.seasonality.all()}
    seasonality_list = []
    for m in range(1, 13):
        if m in existing:
            entry = existing[m]
        else:
            entry = SeasonalityEntry.objects.create(scenario=scenario, month=m, percentage=0)
        est_rev = (total_revenue * (entry.percentage / Decimal('100.0'))).quantize(Decimal('0.01'))
        seasonality_list.append({'month': m, 'month_name': calendar.month_name[m], 'percentage': entry.percentage, 'estimated_revenue': est_rev})

    context = {
        'scenario': scenario,
        'variable_costs_total': variable_costs_total,
        'fixed_costs_total': fixed_costs_total,
        'summary_rows': summary_rows,
        'summary_totals': {
            'revenue': total_revenue,
            'variable': total_variable,
            'contribution': total_revenue - total_variable,
            'fixed': total_fixed,
        },
        'seasonality_list': seasonality_list,
        'total_revenue': total_revenue,
    }
    return render(request, 'costs/scenario_detail.html', context)


def edit_seasonality(request, scenario_id):
    from .models import SeasonalityEntry, CostScenario
    scenario = get_object_or_404(CostScenario, pk=scenario_id)
    if request.method == 'POST':
        for m in range(1, 13):
            key = f'month_{m}'
            val = request.POST.get(key, '0')
            try:
                pct = Decimal(val)
            except Exception:
                pct = Decimal('0')
            entry, _ = SeasonalityEntry.objects.get_or_create(scenario=scenario, month=m)
            entry.percentage = pct
            entry.save()
        messages.success(request, 'Saisonnalité mise à jour.')
        return redirect('scenario-detail', pk=scenario_id)
    else:
        # redirect to scenario detail where form is embedded
        return redirect('scenario-detail', pk=scenario_id)


def save_scenario(request, pk):
    if request.method == "POST":
        messages.success(request, "Scénario sauvegardé.")
    return redirect("scenario-detail", pk=pk)


@transaction.atomic
def duplicate_scenario(request, pk):
    source = CostScenario.objects.prefetch_related("products", "cost_centers", "cost_lines").get(pk=pk)

    cloned = CostScenario.objects.create(
        name=f"{source.name} (copie)",
        period=source.period,
        description=source.description,
        method=source.method,
        input_mode=source.input_mode,
        preset=source.preset,
        ui_mode=source.ui_mode,
        use_reciprocal_allocation=source.use_reciprocal_allocation,
        use_seasonality=source.use_seasonality,
    )

    center_map = {}
    for center in source.cost_centers.all():
        new_center = center.__class__.objects.create(
            scenario=cloned,
            code=center.code,
            name=center.name,
            is_auxiliary=center.is_auxiliary,
        )
        center_map[center.id] = new_center

    product_map = {}
    for product in source.products.all():
        new_product = Product.objects.create(
            scenario=cloned,
            name=product.name,
            quantity=product.quantity,
            unit_price=product.unit_price,
        )
        product_map[product.id] = new_product

    for line in source.cost_lines.all():
        CostLine.objects.create(
            scenario=cloned,
            product=product_map.get(line.product_id),
            label=line.label,
            amount=line.amount,
            center=center_map.get(line.center_id),
            is_direct=line.is_direct,
            is_product=getattr(line, "is_product", False),
        )

    messages.success(request, f"Scénario dupliqué: {cloned.name}")
    return redirect("scenario-detail", pk=cloned.pk)


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
    scenario = get_object_or_404(CostScenario, id=scenario_id)
    if request.method == "POST":
        form = ProductForm(request.POST, scenario=scenario)
        if form.is_valid():
            product = form.save(commit=False)
            product.scenario = scenario
            product.save()
            messages.success(request, f'Le produit « {product.name} » a été ajouté avec succès.')
            return redirect("scenario-detail", pk=scenario.id)
    else:
        form = ProductForm(scenario=scenario)
    return render(request, "costs/add_product.html", {"form": form, "scenario": scenario})


def edit_product(request, scenario_id, product_id):
    scenario = get_object_or_404(CostScenario, id=scenario_id)
    product = get_object_or_404(Product, id=product_id, scenario=scenario)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product, scenario=scenario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Le produit « {product.name} » a été modifié.')
            return redirect("scenario-detail", pk=scenario.id)
    else:
        form = ProductForm(instance=product, scenario=scenario)

    return render(request, "costs/edit_product.html", {"form": form, "scenario": scenario, "product": product})


def delete_product(request, scenario_id, product_id):
    scenario = get_object_or_404(CostScenario, id=scenario_id)
    product = get_object_or_404(Product, id=product_id, scenario=scenario)

    if request.method == "POST":
        product_name = product.name
        product.delete()
        messages.success(request, f'Le produit « {product_name} » a été supprimé.')

    return redirect("scenario-detail", pk=scenario.id)


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

    automatic_results = build_automatic_results(scenario)
    return render(
        request,
        "costs/results.html",
        {
            "scenario": scenario,
            "result": result,
            "automatic_results": automatic_results,
        },
    )


class VariableCostCreateView(CreateView):
    model = VariableCost
    form_class = VariableCostForm
    template_name = 'costs/variable_cost_form.html'
    success_url = "/costs/{scenario_id}/"

    def form_valid(self, form):
        form.instance.scenario = CostScenario.objects.get(pk=self.kwargs['scenario_id'])
        return super().form_valid(form)


class VariableCostUpdateView(UpdateView):
    model = VariableCost
    form_class = VariableCostForm
    template_name = 'costs/variable_cost_form.html'
    success_url = "/costs/{scenario_id}/"

    def form_valid(self, form):
        form.instance.scenario = self.object.scenario
        return super().form_valid(form)


class VariableCostDeleteView(DeleteView):
    model = VariableCost
    template_name = 'costs/variable_cost_confirm_delete.html'

    def get_success_url(self):
        return reverse('scenario-detail', kwargs={'pk': self.object.scenario.pk})


class FixedCostCreateView(CreateView):
    model = FixedCost
    form_class = FixedCostForm
    template_name = 'costs/fixed_cost_form.html'

    def form_valid(self, form):
        form.instance.scenario = CostScenario.objects.get(pk=self.kwargs['scenario_id'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('scenario-detail', kwargs={'pk': self.object.scenario.pk})


class FixedCostUpdateView(UpdateView):
    model = FixedCost
    form_class = FixedCostForm
    template_name = 'costs/fixed_cost_form.html'

    def form_valid(self, form):
        form.instance.scenario = self.object.scenario
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('scenario-detail', kwargs={'pk': self.object.scenario.pk})


class FixedCostDeleteView(DeleteView):
    model = FixedCost
    template_name = 'costs/fixed_cost_confirm_delete.html'

    def get_success_url(self):
        return reverse('scenario-detail', kwargs={'pk': self.object.scenario.pk})