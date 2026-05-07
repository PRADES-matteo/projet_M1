from decimal import Decimal


def calculate_center_analysis(cost_lines):
    total_by_center = {}
    total_general = Decimal("0.00")

    for line in cost_lines:
        total_general += line.amount
        center_name = line.center.name if line.center else "Non affecté"
        total_by_center[center_name] = total_by_center.get(center_name, Decimal("0.00")) + line.amount

    return {
        "total_general": total_general,
        "total_by_center": total_by_center,
    }
