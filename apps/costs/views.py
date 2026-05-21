from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.urls import reverse

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, UpdateView, DeleteView
from django.db.models import Sum, Max
import calendar
from .forms import CostScenarioForm, ProductForm, CostLineForm, VariableCostForm, FixedCostForm
from .models import CostScenario, Product, CostLine, VariableCost, FixedCost, CostCenter, SeasonalityEntry, ScenarioVersion
from .services.direct_costing import calculate_direct_costing
from .services.center_analysis import calculate_center_analysis
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm


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


def _serialize_scenario_snapshot(scenario):
    return {
        "scenario": {
            "name": scenario.name,
            "period": scenario.period,
            "description": scenario.description,
            "method": scenario.method,
            "input_mode": scenario.input_mode,
            "preset": scenario.preset,
            "use_reciprocal_allocation": scenario.use_reciprocal_allocation,
            "use_seasonality": scenario.use_seasonality,
        },
        "cost_centers": [
            {
                "id": center.id,
                "code": center.code,
                "name": center.name,
                "is_auxiliary": center.is_auxiliary,
            }
            for center in scenario.cost_centers.all()
        ],
        "products": [
            {
                "id": product.id,
                "name": product.name,
                "quantity": product.quantity,
                "unit_price": str(product.unit_price),
            }
            for product in scenario.products.all()
        ],
        "cost_lines": [
            {
                "label": line.label,
                "amount": str(line.amount),
                "product_id": line.product_id,
                "center_id": line.center_id,
                "is_direct": line.is_direct,
                "is_product": line.is_product,
            }
            for line in scenario.cost_lines.all()
        ],
        "variable_costs": [
            {
                "name": cost.name,
                "category": cost.category,
                "amount": str(cost.amount),
                "product_id": cost.product_id,
            }
            for cost in scenario.variable_costs.all()
        ],
        "fixed_costs": [
            {
                "name": cost.name,
                "category": cost.category,
                "amount": str(cost.amount),
                "product_id": cost.product_id,
                "is_common": cost.is_common,
            }
            for cost in scenario.fixed_costs.all()
        ],
        "seasonality": [
            {
                "month": entry.month,
                "percentage": str(entry.percentage),
            }
            for entry in scenario.seasonality.all()
        ],
    }


@transaction.atomic
def _restore_scenario_from_snapshot(scenario, snapshot):
    scenario_data = snapshot.get("scenario", {})
    for field in [
        "name", "period", "description", "method", "input_mode",
        "preset", "use_reciprocal_allocation", "use_seasonality",
    ]:
        if field in scenario_data:
            setattr(scenario, field, scenario_data[field])
    scenario.save()

    scenario.variable_costs.all().delete()
    scenario.fixed_costs.all().delete()
    scenario.seasonality.all().delete()
    scenario.cost_lines.all().delete()
    scenario.products.all().delete()
    scenario.cost_centers.all().delete()

    center_id_map = {}
    for center_data in snapshot.get("cost_centers", []):
        new_center = CostCenter.objects.create(
            scenario=scenario,
            code=center_data.get("code", ""),
            name=center_data.get("name", ""),
            is_auxiliary=center_data.get("is_auxiliary", False),
        )
        center_id_map[center_data.get("id")] = new_center

    product_id_map = {}
    for product_data in snapshot.get("products", []):
        new_product = Product.objects.create(
            scenario=scenario,
            name=product_data.get("name", ""),
            quantity=product_data.get("quantity", 0),
            unit_price=product_data.get("unit_price", "0"),
        )
        product_id_map[product_data.get("id")] = new_product

    for line_data in snapshot.get("cost_lines", []):
        CostLine.objects.create(
            scenario=scenario,
            label=line_data.get("label", ""),
            amount=line_data.get("amount", "0"),
            product=product_id_map.get(line_data.get("product_id")),
            center=center_id_map.get(line_data.get("center_id")),
            is_direct=line_data.get("is_direct", False),
            is_product=line_data.get("is_product", False),
        )

    for cost_data in snapshot.get("variable_costs", []):
        VariableCost.objects.create(
            scenario=scenario,
            name=cost_data.get("name", ""),
            category=cost_data.get("category", "Material"),
            amount=cost_data.get("amount", "0"),
            product=product_id_map.get(cost_data.get("product_id")),
        )

    for cost_data in snapshot.get("fixed_costs", []):
        FixedCost.objects.create(
            scenario=scenario,
            name=cost_data.get("name", ""),
            category=cost_data.get("category", "Other"),
            amount=cost_data.get("amount", "0"),
            product=product_id_map.get(cost_data.get("product_id")),
            is_common=cost_data.get("is_common", True),
        )

    for seasonality_data in snapshot.get("seasonality", []):
        SeasonalityEntry.objects.create(
            scenario=scenario,
            month=seasonality_data.get("month", 1),
            percentage=seasonality_data.get("percentage", "0"),
        )


@login_required
def scenario_list(request):
    if request.method == "POST":
        form = CostScenarioForm(request.POST)
        if form.is_valid():
            scenario = form.save(commit=False)
            scenario.user = request.user  # ← associe l'utilisateur
            scenario.save()
            return redirect("scenario-detail", pk=scenario.pk)
    else:
        form = CostScenarioForm()

    scenarios = CostScenario.objects.filter(user=request.user).order_by("-created_at")

    return render(
        request,
        "costs/scenario_list.html",
        {
            "scenarios": scenarios,
            "form": form
        }
    )


@login_required
def scenario_detail(request, pk):
    scenario = get_object_or_404(
        CostScenario.objects.prefetch_related("products", "cost_lines", "cost_lines__center"),
        pk=pk,
        user=request.user  # ← sécurise l'accès
    )
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

        summary_rows.append({
            "product": product,
            "quantity": quantity,
            "unit_price": unit_price,
            "variable_unit_cost": variable_unit_cost,
            "revenue": revenue,
            "variable": variable,
            "fixed": fixed,
            "contribution": contribution,
            "result": result,
        })

        total_revenue += revenue
        total_variable += variable
        total_fixed += fixed

    total_contribution = total_revenue - total_variable
    total_result = total_contribution - total_fixed

    from .models import SeasonalityEntry
    existing = {e.month: e for e in scenario.seasonality.all()}
    seasonality_list = []
    for m in range(1, 13):
        if m in existing:
            entry = existing[m]
        else:
            entry = SeasonalityEntry.objects.create(scenario=scenario, month=m, percentage=0)
        est_rev = (total_revenue * (entry.percentage / Decimal('100.0'))).quantize(Decimal('0.01'))
        seasonality_list.append({
            'month': m,
            'month_name': calendar.month_name[m],
            'percentage': entry.percentage,
            'estimated_revenue': est_rev,
        })

    seasonality_labels = [item['month_name'] for item in seasonality_list]
    seasonality_values = [float(item['percentage']) for item in seasonality_list]

    # Compute automatic summary results (seuil_rentabilite, point_mort, ...)
    automatic_results = build_automatic_results(scenario)
    seuil = automatic_results.get('seuil_rentabilite') or Decimal('0.00')

    # Mark the month where cumulative estimated revenue reaches the break-even threshold
    cumulative = Decimal('0.00')
    break_even_marked = False
    for item in seasonality_list:
        cumulative += Decimal(str(item.get('estimated_revenue') or 0))
        item['cumulative_revenue'] = cumulative
        if not break_even_marked and seuil and cumulative >= seuil:
            item['is_break_even_month'] = True
            break_even_marked = True
        else:
            item['is_break_even_month'] = False

    context = {
        'scenario': scenario,
        'scenario_versions': scenario.versions.all(),
        'all_scenarios': CostScenario.objects.filter(user=request.user).order_by('name'),  # ← filtré
        'current_scenario': scenario,
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
        'seasonality_labels': seasonality_labels,
        'seasonality_values': seasonality_values,
        'total_revenue': total_revenue,
    }
    return render(request, 'costs/scenario_detail.html', context)


@login_required
def edit_seasonality(request, scenario_id):
    scenario = get_object_or_404(CostScenario, pk=scenario_id, user=request.user)
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
    return redirect('scenario-detail', pk=scenario_id)


@login_required
def save_scenario(request, pk):
    scenario = get_object_or_404(CostScenario, pk=pk, user=request.user)
    if request.method == "POST":
        snapshot = _serialize_scenario_snapshot(scenario)
        max_version = scenario.versions.aggregate(max_num=Max('version_number'))['max_num'] or 0
        next_version = max_version + 1
        label = request.POST.get('version_label', '').strip()
        ScenarioVersion.objects.create(
            scenario=scenario,
            version_number=next_version,
            label=label,
            snapshot=snapshot,
        )
        messages.success(request, f"Version v{next_version} sauvegardée.")
    return redirect("scenario-detail", pk=pk)


@login_required
@transaction.atomic
def restore_scenario_version(request, pk, version_id):
    scenario = get_object_or_404(CostScenario, pk=pk, user=request.user)
    version = get_object_or_404(ScenarioVersion, pk=version_id, scenario=scenario)

    if request.method == "POST":
        _restore_scenario_from_snapshot(scenario, version.snapshot)
        messages.success(request, f"Scénario restauré depuis la version v{version.version_number}.")

    return redirect("scenario-detail", pk=pk)


@login_required
def compare_scenarios(request):
    scenarios = CostScenario.objects.filter(user=request.user).order_by('name')
    scenario_a_id = request.GET.get('scenario_a')
    scenario_b_id = request.GET.get('scenario_b')
    scenario_a = None
    scenario_b = None
    comparison = None

    # Provide a list for the second dropdown that excludes scenario_a when present
    scenarios_b = scenarios
    if scenario_a_id:
        scenarios_b = scenarios.exclude(pk=scenario_a_id)

    if scenario_a_id and scenario_b_id:
        scenario_a = get_object_or_404(CostScenario, pk=scenario_a_id, user=request.user)
        scenario_b = get_object_or_404(CostScenario, pk=scenario_b_id, user=request.user)
        auto_a = build_automatic_results(scenario_a)
        auto_b = build_automatic_results(scenario_b)

        comparison = [
            {
                "label": "Chiffre d'affaires",
                "value_a": auto_a["total_revenue"],
                "value_b": auto_b["total_revenue"],
                "delta": auto_a["total_revenue"] - auto_b["total_revenue"],
            },
            {
                "label": "Charges variables",
                "value_a": auto_a["total_variable_costs"],
                "value_b": auto_b["total_variable_costs"],
                "delta": auto_a["total_variable_costs"] - auto_b["total_variable_costs"],
            },
            {
                "label": "Charges fixes",
                "value_a": auto_a["total_fixed_costs"],
                "value_b": auto_b["total_fixed_costs"],
                "delta": auto_a["total_fixed_costs"] - auto_b["total_fixed_costs"],
            },
            {
                "label": "MCV",
                "value_a": auto_a["mcv"],
                "value_b": auto_b["mcv"],
                "delta": auto_a["mcv"] - auto_b["mcv"],
            },
            {
                "label": "Taux de marge (%)",
                "value_a": auto_a["taux_marge"],
                "value_b": auto_b["taux_marge"],
                "delta": auto_a["taux_marge"] - auto_b["taux_marge"],
            },
            {
                "label": "Seuil de rentabilité",
                "value_a": auto_a["seuil_rentabilite"],
                "value_b": auto_b["seuil_rentabilite"],
                "delta": auto_a["seuil_rentabilite"] - auto_b["seuil_rentabilite"],
            },
            {
                "label": "Résultat",
                "value_a": auto_a["resultat"],
                "value_b": auto_b["resultat"],
                "delta": auto_a["resultat"] - auto_b["resultat"],
            },
        ]

    return render(
        request,
        "costs/scenario_compare.html",
        {
            "scenarios": scenarios,
            "scenarios_b": scenarios_b,
            "scenario_a": scenario_a,
            "scenario_b": scenario_b,
            "comparison": comparison,
        },
    )


@login_required
@transaction.atomic
def duplicate_scenario(request, pk):
    source = get_object_or_404(
        CostScenario.objects.prefetch_related("products", "cost_centers", "cost_lines"),
        pk=pk,
        user=request.user  # ← sécurise l'accès
    )

    cloned = CostScenario.objects.create(
        user=request.user,  # ← associe l'utilisateur
        name=f"{source.name} (copie)",
        period=source.period,
        description=source.description,
        method=source.method,
        input_mode=source.input_mode,
        preset=source.preset,
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


@login_required
def create_scenario(request):
    print("Requête POST reçue")
    if request.method == "POST":
        print(request.POST)
        form = CostScenarioForm(request.POST)
        if form.is_valid():
            scenario = form.save(commit=False)
            scenario.user = request.user
            scenario.save()
            return redirect("scenario-detail", pk=scenario.id)
        else:
            print(form.errors)
    else:
        form = CostScenarioForm()
    return render(request, "costs/create_scenario.html", {"form": form})


@login_required
def delete_scenario(request, pk):
    scenario = get_object_or_404(CostScenario, pk=pk)
    if request.method == "POST":
        scenario.delete()
        messages.success(request, f"Le scénario '{scenario.name}' a été supprimé avec succès.")
        return redirect('scenario-list')
    return redirect('scenario-list')


@login_required
def add_product(request, scenario_id):
    scenario = get_object_or_404(CostScenario, id=scenario_id, user=request.user)
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


@login_required
def edit_product(request, scenario_id, product_id):
    scenario = get_object_or_404(CostScenario, id=scenario_id, user=request.user)
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


@login_required
def delete_product(request, scenario_id, product_id):
    scenario = get_object_or_404(CostScenario, id=scenario_id, user=request.user)
    product = get_object_or_404(Product, id=product_id, scenario=scenario)

    if request.method == "POST":
        product_name = product.name
        product.delete()
        messages.success(request, f'Le produit « {product_name} » a été supprimé.')

    return redirect("scenario-detail", pk=scenario.id)


@login_required
def add_cost_line(request, scenario_id, product_id):
    scenario = get_object_or_404(CostScenario, id=scenario_id, user=request.user)
    product = get_object_or_404(Product, id=product_id, scenario=scenario)
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


@login_required
def calculate_results(request, scenario_id):
    scenario = get_object_or_404(CostScenario, id=scenario_id, user=request.user)
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

    def form_valid(self, form):
        form.instance.scenario = get_object_or_404(CostScenario, pk=self.kwargs['scenario_id'], user=self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('scenario-detail', kwargs={'pk': self.object.scenario.pk})


class VariableCostUpdateView(UpdateView):
    model = VariableCost
    form_class = VariableCostForm
    template_name = 'costs/variable_cost_form.html'

    def form_valid(self, form):
        form.instance.scenario = self.object.scenario
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('scenario-detail', kwargs={'pk': self.object.scenario.pk})


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
        form.instance.scenario = get_object_or_404(CostScenario, pk=self.kwargs['scenario_id'], user=self.request.user)
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


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("scenario-list")
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})