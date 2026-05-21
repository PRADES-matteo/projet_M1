from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
from apps.costs.models import CostScenario, Product, CostCenter, CostLine, VariableCost, FixedCost, SeasonalityEntry


class Command(BaseCommand):
    help = "Create demo user and realistic sample scenarios (industriel, commercial, services)"

    def handle(self, *args, **options):
        User = get_user_model()
        with transaction.atomic():
            user, created = User.objects.get_or_create(username="demo")
            if created:
                user.set_password("demo123")
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(self.style.SUCCESS("Created demo user: demo / demo123"))
            else:
                self.stdout.write("Using existing user 'demo'")

            # Helper to create a scenario with data
            def make_scenario(name, preset, period, products_data, fixed_costs, variable_costs, seasonality):
                sc = CostScenario.objects.create(
                    user=user,
                    name=name,
                    period=period,
                    description=f"Scénario exemple: {name}",
                    method="direct_costing",
                    preset=preset,
                    use_seasonality=True,
                )

                # products
                prod_objs = {}
                for p in products_data:
                    prod = Product.objects.create(scenario=sc, name=p['name'], quantity=p['quantity'], unit_price=Decimal(p['unit_price']))
                    prod_objs[p['key']] = prod

                # cost centers
                center = CostCenter.objects.create(scenario=sc, code='C1', name='Centre principal', is_auxiliary=False)

                # cost lines
                for cl in [
                    {'label': 'Matières premières', 'amount': '15000.00', 'product_key': 'p1', 'is_direct': True},
                    {'label': 'Emballage', 'amount': '2000.00', 'product_key': 'p2', 'is_direct': True},
                ]:
                    CostLine.objects.create(
                        scenario=sc,
                        label=cl['label'],
                        amount=Decimal(cl['amount']),
                        product=prod_objs.get(cl['product_key']),
                        center=center,
                        is_direct=cl['is_direct'],
                    )

                # variable costs
                for vc in variable_costs:
                    VariableCost.objects.create(
                        scenario=sc,
                        name=vc['name'],
                        category=vc.get('category', 'Material'),
                        amount=Decimal(vc['amount']),
                        product=prod_objs.get(vc.get('product_key')),
                    )

                # fixed costs
                for fc in fixed_costs:
                    FixedCost.objects.create(
                        scenario=sc,
                        name=fc['name'],
                        category=fc.get('category', 'Other'),
                        amount=Decimal(fc['amount']),
                        product=None,
                        is_common=fc.get('is_common', True),
                    )

                # seasonality
                for month, pct in enumerate(seasonality, start=1):
                    SeasonalityEntry.objects.create(scenario=sc, month=month, percentage=Decimal(str(pct)))

                return sc

            # Industry scenario
            make_scenario(
                name='Industrie Alpha',
                preset='industriel',
                period='Annuel',
                products_data=[
                    {'key': 'p1', 'name': 'Produit A', 'quantity': 1000, 'unit_price': '45.00'},
                    {'key': 'p2', 'name': 'Produit B', 'quantity': 600, 'unit_price': '78.50'},
                ],
                fixed_costs=[
                    {'name': 'Loyer usine', 'amount': '12000.00', 'category': 'Rent'},
                    {'name': 'Salaires', 'amount': '48000.00', 'category': 'Salary'},
                ],
                variable_costs=[
                    {'name': 'Consommables', 'amount': '8000.00', 'product_key': 'p1'},
                    {'name': 'Main d\'oeuvre directe', 'amount': '15000.00', 'product_key': 'p2'},
                ],
                seasonality=[5,5,8,9,10,12,10,10,8,7,8,8],
            )

            # Commercial scenario
            make_scenario(
                name='Commerce Beta',
                preset='commercial',
                period='Annuel',
                products_data=[
                    {'key': 'p1', 'name': 'Article X', 'quantity': 2000, 'unit_price': '12.50'},
                    {'key': 'p2', 'name': 'Article Y', 'quantity': 1500, 'unit_price': '9.75'},
                ],
                fixed_costs=[
                    {'name': 'Boutique loyer', 'amount': '18000.00', 'category': 'Rent'},
                    {'name': 'Marketing', 'amount': '6000.00', 'category': 'Other'},
                ],
                variable_costs=[
                    {'name': 'Frais d\'achat', 'amount': '25000.00'},
                    {'name': 'Emballage', 'amount': '3000.00'},
                ],
                seasonality=[6,6,7,8,9,10,11,10,8,7,9,9],
            )

            # Services scenario
            make_scenario(
                name='Services Gamma',
                preset='services',
                period='Annuel',
                products_data=[
                    {'key': 'p1', 'name': 'Prestation Standard', 'quantity': 500, 'unit_price': '250.00'},
                ],
                fixed_costs=[
                    {'name': 'Salaires', 'amount': '60000.00', 'category': 'Salary'},
                    {'name': 'Assurances', 'amount': '4000.00', 'category': 'Other'},
                ],
                variable_costs=[
                    {'name': 'Déplacements', 'amount': '7000.00'},
                ],
                seasonality=[7,7,8,8,9,10,10,9,8,7,7,8],
            )

            self.stdout.write(self.style.SUCCESS('Demo scenarios created and assigned to user "demo".'))