from decimal import Decimal


def calculate_center_analysis(lines):
    total_general = Decimal("0.00")
    total_by_center = {}

    for line in lines:
        total_general += line.amount
        center_name = line.center.name if line.center else "Non affecté"
        if center_name not in total_by_center:
            total_by_center[center_name] = Decimal("0.00")
        total_by_center[center_name] += line.amount

    return {
        "total_general": total_general,
        "total_by_center": total_by_center,
    }