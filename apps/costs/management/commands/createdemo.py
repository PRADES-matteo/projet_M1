from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
from apps.costs.models import (
    CostScenario, Product, CostCenter, CostCenterAllocation,
    CostLine, VariableCost, FixedCost, SeasonalityEntry, ProductCenterUsage,
)


class Command(BaseCommand):
    help = "Create demo user and realistic sample scenarios (industriel, commercial, services, centres d'analyse)"

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

            # ----------------------------------------------------------------
            # Helper : direct costing scenarios (unchanged)
            # ----------------------------------------------------------------
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

                prod_objs = {}
                for p in products_data:
                    prod = Product.objects.create(
                        scenario=sc,
                        name=p['name'],
                        quantity=p['quantity'],
                        unit_price=Decimal(p['unit_price']),
                    )
                    prod_objs[p['key']] = prod

                center = CostCenter.objects.create(
                    scenario=sc, code='C1', name='Centre principal', is_auxiliary=False,
                )

                for cl in [
                    {'label': 'Matières premières', 'amount': '15000.00', 'product_key': 'p1', 'is_direct': True},
                    {'label': 'Emballage',           'amount': '2000.00',  'product_key': 'p2', 'is_direct': True},
                ]:
                    CostLine.objects.create(
                        scenario=sc,
                        label=cl['label'],
                        amount=Decimal(cl['amount']),
                        product=prod_objs.get(cl['product_key']),
                        center=center,
                        is_direct=cl['is_direct'],
                    )

                for vc in variable_costs:
                    VariableCost.objects.create(
                        scenario=sc,
                        name=vc['name'],
                        category=vc.get('category', 'Material'),
                        amount=Decimal(vc['amount']),
                        product=prod_objs.get(vc.get('product_key')),
                    )

                for fc in fixed_costs:
                    FixedCost.objects.create(
                        scenario=sc,
                        name=fc['name'],
                        category=fc.get('category', 'Other'),
                        amount=Decimal(fc['amount']),
                        product=None,
                        is_common=fc.get('is_common', True),
                    )

                for month, pct in enumerate(seasonality, start=1):
                    SeasonalityEntry.objects.create(
                        scenario=sc, month=month, percentage=Decimal(str(pct)),
                    )

                return sc

            # ----------------------------------------------------------------
            # Helper : centre d'analyse scenarios
            # ----------------------------------------------------------------
            def make_center_scenario(name, preset, period, description, products_data,
                                     centers_data, cost_lines_data, allocations_data,
                                     usages_data, seasonality):
                """
                products_data  : [{'key', 'name', 'quantity', 'unit_price'}]
                centers_data   : [{'key', 'code', 'name', 'is_auxiliary', 'unit_of_work', 'total_units'}]
                cost_lines_data: [{'label', 'amount', 'center_key'}]
                allocations_data:[{'from_key', 'to_key', 'percentage'}]
                usages_data    : [{'product_key', 'center_key', 'units_used'}]
                """
                sc = CostScenario.objects.create(
                    user=user,
                    name=name,
                    period=period,
                    description=description,
                    method="center_analysis",
                    preset=preset,
                    use_seasonality=True,
                )

                # Produits
                prod_objs = {}
                for p in products_data:
                    prod = Product.objects.create(
                        scenario=sc,
                        name=p['name'],
                        quantity=p['quantity'],
                        unit_price=Decimal(p['unit_price']),
                    )
                    prod_objs[p['key']] = prod

                # Centres d'analyse
                center_objs = {}
                for c in centers_data:
                    center = CostCenter.objects.create(
                        scenario=sc,
                        code=c['code'],
                        name=c['name'],
                        is_auxiliary=c.get('is_auxiliary', False),
                        unit_of_work=c.get('unit_of_work', ''),
                        total_units=Decimal(str(c.get('total_units', 0))),
                    )
                    center_objs[c['key']] = center

                # Charges primaires (lignes de coût affectées aux centres)
                for cl in cost_lines_data:
                    CostLine.objects.create(
                        scenario=sc,
                        label=cl['label'],
                        amount=Decimal(cl['amount']),
                        center=center_objs[cl['center_key']],
                        is_direct=False,
                        is_product=False,
                    )

                # Répartitions des centres auxiliaires
                for alloc in allocations_data:
                    CostCenterAllocation.objects.create(
                        scenario=sc,
                        from_center=center_objs[alloc['from_key']],
                        to_center=center_objs[alloc['to_key']],
                        percentage=Decimal(str(alloc['percentage'])),
                    )

                # Unités d'œuvre par produit × centre
                for u in usages_data:
                    ProductCenterUsage.objects.create(
                        product=prod_objs[u['product_key']],
                        center=center_objs[u['center_key']],
                        units_used=Decimal(str(u['units_used'])),
                    )

                # Saisonnalité
                for month, pct in enumerate(seasonality, start=1):
                    SeasonalityEntry.objects.create(
                        scenario=sc, month=month, percentage=Decimal(str(pct)),
                    )

                return sc

            # ----------------------------------------------------------------
            # Scénarios direct costing (inchangés)
            # ----------------------------------------------------------------
            make_scenario(
                name='Industrie Alpha',
                preset='industriel',
                period='Annuel',
                products_data=[
                    {'key': 'p1', 'name': 'Produit A', 'quantity': 1000, 'unit_price': '45.00'},
                    {'key': 'p2', 'name': 'Produit B', 'quantity':  600, 'unit_price': '78.50'},
                ],
                fixed_costs=[
                    {'name': 'Loyer usine', 'amount': '12000.00', 'category': 'Rent'},
                    {'name': 'Salaires',    'amount': '48000.00', 'category': 'Salary'},
                ],
                variable_costs=[
                    {'name': 'Consommables',            'amount':  '8000.00', 'product_key': 'p1'},
                    {'name': "Main d'oeuvre directe",   'amount': '15000.00', 'product_key': 'p2'},
                ],
                seasonality=[5, 5, 8, 9, 10, 12, 10, 10, 8, 7, 8, 8],
            )

            make_scenario(
                name='Commerce Beta',
                preset='commercial',
                period='Annuel',
                products_data=[
                    {'key': 'p1', 'name': 'Article X', 'quantity': 2000, 'unit_price': '12.50'},
                    {'key': 'p2', 'name': 'Article Y', 'quantity': 1500, 'unit_price':  '9.75'},
                ],
                fixed_costs=[
                    {'name': 'Boutique loyer', 'amount': '18000.00', 'category': 'Rent'},
                    {'name': 'Marketing',      'amount':  '6000.00', 'category': 'Other'},
                ],
                variable_costs=[
                    {'name': "Frais d'achat", 'amount': '25000.00'},
                    {'name': 'Emballage',     'amount':  '3000.00'},
                ],
                seasonality=[6, 6, 7, 8, 9, 10, 11, 10, 8, 7, 9, 9],
            )

            make_scenario(
                name='Services Gamma',
                preset='services',
                period='Annuel',
                products_data=[
                    {'key': 'p1', 'name': 'Prestation Standard', 'quantity': 500, 'unit_price': '250.00'},
                ],
                fixed_costs=[
                    {'name': 'Salaires',   'amount': '60000.00', 'category': 'Salary'},
                    {'name': 'Assurances', 'amount':  '4000.00', 'category': 'Other'},
                ],
                variable_costs=[
                    {'name': 'Déplacements', 'amount': '7000.00'},
                ],
                seasonality=[7, 7, 8, 8, 9, 10, 10, 9, 8, 7, 7, 8],
            )

            # ----------------------------------------------------------------
            # Scénario 1 — Centres d'analyse : menuiserie industrielle
            # Deux centres auxiliaires (Entretien, Énergie) qui se répartissent
            # vers deux centres principaux (Débit, Assemblage).
            # Produits : Fenêtre PVC et Porte bois.
            # Unité d'œuvre : heure machine (Débit) et heure main d'œuvre (Assemblage).
            # ----------------------------------------------------------------
            make_center_scenario(
                name='Menuiserie Delta — Centres',
                preset='industriel',
                period='Annuel',
                description=(
                    "Exemple centres d'analyse : menuiserie industrielle. "
                    "Centres auxiliaires Entretien et Énergie répartis vers "
                    "Débit et Assemblage. Unités d'œuvre : h/machine et h/MOD."
                ),
                products_data=[
                    {'key': 'p1', 'name': 'Fenêtre PVC',  'quantity': 400, 'unit_price': '320.00'},
                    {'key': 'p2', 'name': 'Porte bois',   'quantity': 250, 'unit_price': '480.00'},
                ],
                centers_data=[
                    # Auxiliaires
                    {'key': 'aux_entretien', 'code': 'ENT', 'name': 'Entretien',
                     'is_auxiliary': True,  'unit_of_work': '',          'total_units': 0},
                    {'key': 'aux_energie',   'code': 'ENE', 'name': 'Énergie',
                     'is_auxiliary': True,  'unit_of_work': '',          'total_units': 0},
                    # Principaux
                    {'key': 'debit',         'code': 'DEB', 'name': 'Centre Débit',
                     'is_auxiliary': False, 'unit_of_work': 'heure machine', 'total_units': 2000},
                    {'key': 'assemblage',    'code': 'ASM', 'name': 'Centre Assemblage',
                     'is_auxiliary': False, 'unit_of_work': 'heure MOD',     'total_units': 3000},
                ],
                cost_lines_data=[
                    # Entretien
                    {'label': 'Salaires entretien',       'amount': '18000.00', 'center_key': 'aux_entretien'},
                    {'label': 'Fournitures entretien',    'amount':  '4000.00', 'center_key': 'aux_entretien'},
                    # Énergie
                    {'label': 'Électricité',              'amount': '12000.00', 'center_key': 'aux_energie'},
                    {'label': 'Gaz industriel',           'amount':  '5000.00', 'center_key': 'aux_energie'},
                    # Débit (charges directes)
                    {'label': 'Amortissement machines',   'amount': '24000.00', 'center_key': 'debit'},
                    {'label': 'Salaires opérateurs débit','amount': '36000.00', 'center_key': 'debit'},
                    # Assemblage (charges directes)
                    {'label': 'Salaires monteurs',        'amount': '45000.00', 'center_key': 'assemblage'},
                    {'label': 'Outillage assemblage',     'amount':  '8000.00', 'center_key': 'assemblage'},
                ],
                allocations_data=[
                    # Entretien → 60 % Débit, 40 % Assemblage
                    {'from_key': 'aux_entretien', 'to_key': 'debit',      'percentage': 60},
                    {'from_key': 'aux_entretien', 'to_key': 'assemblage', 'percentage': 40},
                    # Énergie → 70 % Débit, 30 % Assemblage
                    {'from_key': 'aux_energie',   'to_key': 'debit',      'percentage': 70},
                    {'from_key': 'aux_energie',   'to_key': 'assemblage', 'percentage': 30},
                ],
                usages_data=[
                    # Fenêtre PVC : 800 h/machine débit, 1 200 h/MOD assemblage
                    {'product_key': 'p1', 'center_key': 'debit',      'units_used': 800},
                    {'product_key': 'p1', 'center_key': 'assemblage', 'units_used': 1200},
                    # Porte bois : 1 200 h/machine débit, 1 800 h/MOD assemblage
                    {'product_key': 'p2', 'center_key': 'debit',      'units_used': 1200},
                    {'product_key': 'p2', 'center_key': 'assemblage', 'units_used': 1800},
                ],
                seasonality=[5, 5, 8, 9, 10, 12, 10, 10, 8, 7, 8, 8],
            )

            # ----------------------------------------------------------------
            # Scénario 2 — Centres d'analyse : agence de communication
            # Un seul centre auxiliaire (Administration) réparti vers
            # trois centres principaux (Création, Production, Conseil).
            # Produits : Campagne web et Identité visuelle.
            # Unité d'œuvre : heure créa (Création), heure prod (Production),
            #                 mission (Conseil).
            # ----------------------------------------------------------------
            make_center_scenario(
                name='Agence Epsilon — Centres',
                preset='services',
                period='Annuel',
                description=(
                    "Exemple centres d'analyse : agence de communication. "
                    "Centre auxiliaire Administration réparti vers Création, "
                    "Production et Conseil. Unités d'œuvre : h/créa, h/prod, mission."
                ),
                products_data=[
                    {'key': 'p1', 'name': 'Campagne web',      'quantity': 30, 'unit_price': '8500.00'},
                    {'key': 'p2', 'name': 'Identité visuelle', 'quantity': 20, 'unit_price': '5200.00'},
                ],
                centers_data=[
                    # Auxiliaire
                    {'key': 'admin',      'code': 'ADM', 'name': 'Administration',
                     'is_auxiliary': True,  'unit_of_work': '',         'total_units': 0},
                    # Principaux
                    {'key': 'creation',   'code': 'CRE', 'name': 'Création',
                     'is_auxiliary': False, 'unit_of_work': 'heure créa',  'total_units': 1500},
                    {'key': 'production', 'code': 'PRO', 'name': 'Production',
                     'is_auxiliary': False, 'unit_of_work': 'heure prod',  'total_units': 800},
                    {'key': 'conseil',    'code': 'CON', 'name': 'Conseil',
                     'is_auxiliary': False, 'unit_of_work': 'mission',     'total_units': 50},
                ],
                cost_lines_data=[
                    # Administration
                    {'label': 'Salaires administratifs', 'amount': '28000.00', 'center_key': 'admin'},
                    {'label': 'Loyer bureaux (quote-part admin)', 'amount': '6000.00', 'center_key': 'admin'},
                    # Création
                    {'label': 'Salaires créatifs',       'amount': '55000.00', 'center_key': 'creation'},
                    {'label': 'Licences logiciels',      'amount':  '8000.00', 'center_key': 'creation'},
                    # Production
                    {'label': 'Salaires techniciens',    'amount': '32000.00', 'center_key': 'production'},
                    {'label': 'Matériel production',     'amount':  '5000.00', 'center_key': 'production'},
                    # Conseil
                    {'label': 'Salaires consultants',    'amount': '42000.00', 'center_key': 'conseil'},
                    {'label': 'Déplacements conseil',    'amount':  '4000.00', 'center_key': 'conseil'},
                ],
                allocations_data=[
                    # Administration → 40 % Création, 30 % Production, 30 % Conseil
                    {'from_key': 'admin', 'to_key': 'creation',   'percentage': 40},
                    {'from_key': 'admin', 'to_key': 'production', 'percentage': 30},
                    {'from_key': 'admin', 'to_key': 'conseil',    'percentage': 30},
                ],
                usages_data=[
                    # Campagne web : 900 h créa, 500 h prod, 25 missions conseil
                    {'product_key': 'p1', 'center_key': 'creation',   'units_used': 900},
                    {'product_key': 'p1', 'center_key': 'production', 'units_used': 500},
                    {'product_key': 'p1', 'center_key': 'conseil',    'units_used': 25},
                    # Identité visuelle : 600 h créa, 300 h prod, 25 missions conseil
                    {'product_key': 'p2', 'center_key': 'creation',   'units_used': 600},
                    {'product_key': 'p2', 'center_key': 'production', 'units_used': 300},
                    {'product_key': 'p2', 'center_key': 'conseil',    'units_used': 25},
                ],
                seasonality=[7, 7, 8, 8, 9, 10, 10, 9, 8, 7, 7, 8],
            )

            # ----------------------------------------------------------------
            # Scénario 3 — Centres d'analyse : distribution commerciale
            # Un centre auxiliaire (Logistique) réparti vers trois centres
            # principaux (Réception, Mise en rayon, Expédition).
            # Produits : Référence L et Référence M.
            # ----------------------------------------------------------------
            make_center_scenario(
                name='Distribution Kappa — Centres',
                preset='commercial',
                period='Annuel',
                description=(
                    "Exemple centres d'analyse : distribution commerciale. "
                    "Centre auxiliaire Logistique réparti vers Réception, "
                    "Mise en rayon et Expédition. Unités d'œuvre : palette, h/travail, colis."
                ),
                products_data=[
                    {'key': 'p1', 'name': 'Référence L', 'quantity': 2000, 'unit_price': '25.00'},
                    {'key': 'p2', 'name': 'Référence M', 'quantity': 1200, 'unit_price': '45.00'},
                ],
                centers_data=[
                    # Auxiliaire
                    {'key': 'logistique', 'code': 'LOG', 'name': 'Logistique commune',
                     'is_auxiliary': True,  'unit_of_work': '',              'total_units': 0},
                    # Principaux
                    {'key': 'reception',  'code': 'REC', 'name': 'Réception',
                     'is_auxiliary': False, 'unit_of_work': 'palette traitée', 'total_units': 500},
                    {'key': 'rayon',      'code': 'MRY', 'name': 'Mise en rayon',
                     'is_auxiliary': False, 'unit_of_work': 'heure travail',   'total_units': 1200},
                    {'key': 'expedition', 'code': 'EXP', 'name': 'Expédition',
                     'is_auxiliary': False, 'unit_of_work': 'colis expédié',   'total_units': 3200},
                ],
                cost_lines_data=[
                    # Logistique
                    {'label': 'Salaires logistique',     'amount': '20000.00', 'center_key': 'logistique'},
                    {'label': 'Assurances entrepôt',     'amount':  '5000.00', 'center_key': 'logistique'},
                    # Réception
                    {'label': 'Salaires réception',      'amount': '18000.00', 'center_key': 'reception'},
                    {'label': 'Matériel manutention',    'amount':  '6000.00', 'center_key': 'reception'},
                    # Mise en rayon
                    {'label': 'Salaires mise en rayon',  'amount': '22000.00', 'center_key': 'rayon'},
                    {'label': 'Fournitures',             'amount':  '3000.00', 'center_key': 'rayon'},
                    # Expédition
                    {'label': 'Salaires expédition',     'amount': '28000.00', 'center_key': 'expedition'},
                    {'label': 'Emballages',              'amount':  '8000.00', 'center_key': 'expedition'},
                ],
                allocations_data=[
                    # Logistique → 30 % Réception, 40 % Mise en rayon, 30 % Expédition
                    {'from_key': 'logistique', 'to_key': 'reception',  'percentage': 30},
                    {'from_key': 'logistique', 'to_key': 'rayon',      'percentage': 40},
                    {'from_key': 'logistique', 'to_key': 'expedition', 'percentage': 30},
                ],
                usages_data=[
                    # Référence L : 200 palettes, 700 h rayon, 2000 colis
                    {'product_key': 'p1', 'center_key': 'reception',  'units_used': 200},
                    {'product_key': 'p1', 'center_key': 'rayon',      'units_used': 700},
                    {'product_key': 'p1', 'center_key': 'expedition', 'units_used': 2000},
                    # Référence M : 300 palettes, 500 h rayon, 1200 colis
                    {'product_key': 'p2', 'center_key': 'reception',  'units_used': 300},
                    {'product_key': 'p2', 'center_key': 'rayon',      'units_used': 500},
                    {'product_key': 'p2', 'center_key': 'expedition', 'units_used': 1200},
                ],
                seasonality=[6, 6, 7, 8, 9, 10, 11, 10, 8, 7, 9, 9],
            )

            # ----------------------------------------------------------------
            # Helper : direct costing évolué (CF communes + spécifiques)
            # ----------------------------------------------------------------
            def make_advanced_scenario(name, preset, period, products_data,
                                       variable_costs, fixed_costs, seasonality):
                sc = CostScenario.objects.create(
                    user=user,
                    name=name,
                    period=period,
                    description=f"Scénario exemple direct costing évolué : {name}",
                    method="direct_costing_advanced",
                    preset=preset,
                    use_seasonality=True,
                )

                prod_objs = {}
                for p in products_data:
                    prod = Product.objects.create(
                        scenario=sc,
                        name=p['name'],
                        quantity=p['quantity'],
                        unit_price=Decimal(p['unit_price']),
                    )
                    prod_objs[p['key']] = prod

                for vc in variable_costs:
                    VariableCost.objects.create(
                        scenario=sc,
                        name=vc['name'],
                        category=vc.get('category', 'Material'),
                        amount=Decimal(vc['amount']),
                        product=prod_objs.get(vc.get('product_key')),
                    )

                for fc in fixed_costs:
                    product_key = fc.get('product_key')
                    FixedCost.objects.create(
                        scenario=sc,
                        name=fc['name'],
                        category=fc.get('category', 'Other'),
                        amount=Decimal(fc['amount']),
                        product=prod_objs.get(product_key) if product_key else None,
                        is_common=fc.get('is_common', True),
                    )

                for month, pct in enumerate(seasonality, start=1):
                    SeasonalityEntry.objects.create(
                        scenario=sc, month=month, percentage=Decimal(str(pct)),
                    )

                return sc

            # ----------------------------------------------------------------
            # Direct costing évolué — Industriel
            # Produits : Produit X et Produit Y.
            # CF communes : loyer, salaires direction.
            # CF spécifiques : amortissement machine par produit.
            # ----------------------------------------------------------------
            make_advanced_scenario(
                name='Industrie Zeta — Évolué',
                preset='industriel',
                period='Annuel',
                products_data=[
                    {'key': 'p1', 'name': 'Produit X', 'quantity': 800, 'unit_price': '65.00'},
                    {'key': 'p2', 'name': 'Produit Y', 'quantity': 500, 'unit_price': '95.00'},
                ],
                variable_costs=[
                    {'name': 'Matières premières X', 'category': 'Material', 'amount': '12000.00', 'product_key': 'p1'},
                    {'name': "Main d'œuvre X",        'category': 'Labor',    'amount':  '8000.00', 'product_key': 'p1'},
                    {'name': 'Matières premières Y', 'category': 'Material', 'amount': '15000.00', 'product_key': 'p2'},
                    {'name': "Main d'œuvre Y",        'category': 'Labor',    'amount': '10000.00', 'product_key': 'p2'},
                    {'name': 'Énergie variable',     'category': 'Overhead', 'amount':  '5000.00'},
                ],
                fixed_costs=[
                    # CF communes
                    {'name': 'Loyer usine',          'category': 'Rent',        'amount': '15000.00', 'is_common': True},
                    {'name': 'Salaires direction',   'category': 'Salary',      'amount': '42000.00', 'is_common': True},
                    {'name': 'Amort. bâtiment',      'category': 'Depreciation','amount':  '8000.00', 'is_common': True},
                    # CF spécifiques
                    {'name': 'Amort. ligne Produit X','category': 'Depreciation','amount': '18000.00', 'is_common': False, 'product_key': 'p1'},
                    {'name': 'Contrôle qualité X',   'category': 'Other',       'amount':  '6000.00', 'is_common': False, 'product_key': 'p1'},
                    {'name': 'Amort. ligne Produit Y','category': 'Depreciation','amount': '22000.00', 'is_common': False, 'product_key': 'p2'},
                ],
                seasonality=[5, 5, 8, 9, 10, 12, 10, 10, 8, 7, 8, 8],
            )

            # ----------------------------------------------------------------
            # Direct costing évolué — Commercial
            # Produits : Gamme A, Gamme B, Gamme C.
            # CF communes : loyer boutique, frais généraux, salaires accueil.
            # CF spécifiques : publicité et SAV par gamme.
            # ----------------------------------------------------------------
            make_advanced_scenario(
                name='Commerce Eta — Évolué',
                preset='commercial',
                period='Annuel',
                products_data=[
                    {'key': 'p1', 'name': 'Gamme A', 'quantity': 3000, 'unit_price': '18.00'},
                    {'key': 'p2', 'name': 'Gamme B', 'quantity': 1500, 'unit_price': '32.00'},
                    {'key': 'p3', 'name': 'Gamme C', 'quantity':  800, 'unit_price': '55.00'},
                ],
                variable_costs=[
                    {'name': 'Achat marchandises A', 'category': 'Material', 'amount': '32000.00', 'product_key': 'p1'},
                    {'name': 'Transport A',           'category': 'Overhead', 'amount':  '3000.00', 'product_key': 'p1'},
                    {'name': 'Achat marchandises B', 'category': 'Material', 'amount': '24000.00', 'product_key': 'p2'},
                    {'name': 'Transport B',           'category': 'Overhead', 'amount':  '2500.00', 'product_key': 'p2'},
                    {'name': 'Achat marchandises C', 'category': 'Material', 'amount': '20000.00', 'product_key': 'p3'},
                    {'name': 'Commission vente C',    'category': 'Labor',    'amount':  '4000.00', 'product_key': 'p3'},
                ],
                fixed_costs=[
                    # CF communes
                    {'name': 'Loyer boutique',   'category': 'Rent',   'amount': '24000.00', 'is_common': True},
                    {'name': 'Frais généraux',   'category': 'Other',  'amount':  '8000.00', 'is_common': True},
                    {'name': 'Salaires accueil', 'category': 'Salary', 'amount': '18000.00', 'is_common': True},
                    # CF spécifiques
                    {'name': 'Publicité Gamme A', 'category': 'Other', 'amount': '5000.00', 'is_common': False, 'product_key': 'p1'},
                    {'name': 'SAV Gamme B',       'category': 'Other', 'amount': '3000.00', 'is_common': False, 'product_key': 'p2'},
                    {'name': 'Publicité Gamme C', 'category': 'Other', 'amount': '8000.00', 'is_common': False, 'product_key': 'p3'},
                ],
                seasonality=[6, 6, 7, 8, 9, 10, 11, 10, 8, 7, 9, 9],
            )

            # ----------------------------------------------------------------
            # Direct costing évolué — Services
            # Produits : Consulting RH et Formation Pro.
            # CF communes : salaires fixes, loyer, assurance.
            # CF spécifiques : certification et salle par prestation.
            # ----------------------------------------------------------------
            make_advanced_scenario(
                name='Services Iota — Évolué',
                preset='services',
                period='Annuel',
                products_data=[
                    {'key': 'p1', 'name': 'Consulting RH',  'quantity': 80, 'unit_price': '1800.00'},
                    {'key': 'p2', 'name': 'Formation Pro',  'quantity': 60, 'unit_price': '1200.00'},
                ],
                variable_costs=[
                    {'name': 'Déplacements RH',      'category': 'Overhead', 'amount':  '8000.00', 'product_key': 'p1'},
                    {'name': 'Sous-traitance RH',    'category': 'Labor',    'amount': '12000.00', 'product_key': 'p1'},
                    {'name': 'Supports formation',   'category': 'Material', 'amount':  '4000.00', 'product_key': 'p2'},
                    {'name': 'Intervenants externes','category': 'Labor',    'amount':  '9000.00', 'product_key': 'p2'},
                ],
                fixed_costs=[
                    # CF communes
                    {'name': 'Salaires fixes',      'category': 'Salary', 'amount': '72000.00', 'is_common': True},
                    {'name': 'Loyer bureaux',       'category': 'Rent',   'amount': '14400.00', 'is_common': True},
                    {'name': 'Assurance entreprise','category': 'Other',  'amount':  '3600.00', 'is_common': True},
                    # CF spécifiques
                    {'name': 'Certification RH',  'category': 'Other', 'amount': '5000.00', 'is_common': False, 'product_key': 'p1'},
                    {'name': 'Location salle',    'category': 'Rent',  'amount': '9000.00', 'is_common': False, 'product_key': 'p2'},
                ],
                seasonality=[7, 7, 8, 8, 9, 10, 10, 9, 8, 7, 7, 8],
            )

            self.stdout.write(self.style.SUCCESS(
                'Demo scenarios created and assigned to user "demo".\n'
                '  Direct costing simple:\n'
                '    - Industrie Alpha (industriel)\n'
                '    - Commerce Beta (commercial)\n'
                '    - Services Gamma (services)\n'
                '  Direct costing évolué:\n'
                '    - Industrie Zeta — Évolué (industriel)\n'
                '    - Commerce Eta — Évolué (commercial)\n'
                '    - Services Iota — Évolué (services)\n'
                '  Centres d\'analyse:\n'
                '    - Menuiserie Delta — Centres (industriel)\n'
                '    - Agence Epsilon — Centres (services)\n'
                '    - Distribution Kappa — Centres (commercial)\n'
            ))