from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.costs.services.center_analysis import calculate_center_analysis
from apps.costs.services.direct_costing import calculate_direct_costing


class CalculationTests(SimpleTestCase):
    def make_line(self, amount, center=None, is_direct=False):
        center_obj = SimpleNamespace(name=center) if center else None
        return SimpleNamespace(amount=Decimal(amount), center=center_obj, is_direct=is_direct)

    def test_center_analysis_totals(self):
        lines = [
            self.make_line("100.00", center="A"),
            self.make_line("50.00", center="A"),
            self.make_line("25.00", center="B"),
            self.make_line("10.00", center=None),
        ]
        result = calculate_center_analysis(lines)
        self.assertEqual(result["total_general"], Decimal("185.00"))
        self.assertEqual(result["total_by_center"]["A"], Decimal("150.00"))
        self.assertEqual(result["total_by_center"]["B"], Decimal("25.00"))
        self.assertEqual(result["total_by_center"]["Non affecté"], Decimal("10.00"))

    def test_direct_costing_sums(self):
        lines = [
            self.make_line("120.00", is_direct=True),
            self.make_line("30.00", is_direct=False),
            self.make_line("50.00", is_direct=True),
        ]
        result = calculate_direct_costing(lines)
        self.assertEqual(result["direct_costs"], Decimal("170.00"))
        self.assertEqual(result["indirect_costs"], Decimal("30.00"))
        self.assertEqual(result["total_cost"], Decimal("200.00"))
