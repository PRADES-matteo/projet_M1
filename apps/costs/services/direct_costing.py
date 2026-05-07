from decimal import Decimal


def calculate_direct_costing(cost_lines):
    direct_costs = Decimal("0.00")
    indirect_costs = Decimal("0.00")

    for line in cost_lines:
        if line.is_direct:
            direct_costs += line.amount
        else:
            indirect_costs += line.amount

    total_cost = direct_costs + indirect_costs
    return {
        "direct_costs": direct_costs,
        "indirect_costs": indirect_costs,
        "total_cost": total_cost,
    }
