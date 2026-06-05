from decimal import Decimal


def calculate_center_analysis_full(scenario):
    centers = list(scenario.cost_centers.prefetch_related("cost_lines", "product_usages").all())
    allocations = list(scenario.allocations.select_related("from_center", "to_center").all())
    products = list(scenario.products.prefetch_related("center_usages__center").all())

    center_map = {c.id: c for c in centers}

    # 1. Charges primaires de chaque centre
    primary_costs = {}
    for center in centers:
        primary_costs[center.id] = sum(
            (line.amount for line in center.cost_lines.all()),
            Decimal("0.00")
        )

    # 2. Répartition des centres auxiliaires → centres principaux
    secondary_costs = dict(primary_costs)
    auxiliary_centers = [c for c in centers if c.is_auxiliary]

    for aux in auxiliary_centers:
        aux_total = secondary_costs.get(aux.id, Decimal("0.00"))
        aux_allocations = [a for a in allocations if a.from_center_id == aux.id]
        for alloc in aux_allocations:
            transferred = (aux_total * alloc.percentage / Decimal("100")).quantize(Decimal("0.01"))
            secondary_costs[alloc.to_center_id] = (
                secondary_costs.get(alloc.to_center_id, Decimal("0.00")) + transferred
            )
        secondary_costs[aux.id] = Decimal("0.00")

    # 3. Taux de cession par centre principal
    principal_centers = [c for c in centers if not c.is_auxiliary]
    taux = {}
    for center in principal_centers:
        total_units = center.total_units or Decimal("1")
        taux[center.id] = (
            secondary_costs.get(center.id, Decimal("0.00")) / total_units
        ).quantize(Decimal("0.0001"))

    # 4. Coût de revient par produit
    product_results = []
    for product in products:
        cost_from_centers = Decimal("0.00")
        center_detail = []

        for usage in product.center_usages.all():
            if not usage.center.is_auxiliary and usage.center_id in taux:
                cost = (taux[usage.center_id] * usage.units_used).quantize(Decimal("0.01"))
                cost_from_centers += cost
                center_detail.append({
                    "center": usage.center,
                    "units_used": usage.units_used,
                    "taux": taux[usage.center_id],
                    "cost": cost,
                })

        revenue = Decimal(str(product.unit_price)) * Decimal(str(product.quantity))
        unit_cost = (cost_from_centers / Decimal(str(product.quantity))) if product.quantity else Decimal("0.00")
        profit = revenue - cost_from_centers
        profitability_rate = (
            (profit / revenue * Decimal("100")).quantize(Decimal("0.01"))
            if revenue else Decimal("0.00")
        )

        product_results.append({
            "product": product,
            "revenue": revenue,
            "total_cost": cost_from_centers,
            "unit_cost": unit_cost,
            "profit": profit,
            "profitability_rate": profitability_rate,
            "center_detail": center_detail,
        })

    return {
        "centers": centers,
        "principal_centers": principal_centers,
        "auxiliary_centers": auxiliary_centers,
        "primary_costs": primary_costs,
        "secondary_costs": secondary_costs,
        "taux": taux,
        "product_results": product_results,
        "allocations": allocations,
    }