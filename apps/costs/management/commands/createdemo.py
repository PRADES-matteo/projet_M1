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
            # Helper : direct costing simple
            # ----------------------------------------------------------------
            def make_scenario(name, preset, period, description, products_data,
                               fixed_costs, variable_costs, seasonality):
                sc = CostScenario.objects.create(
                    user=user,
                    name=name,
                    period=period,
                    description=description,
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
                sc = CostScenario.objects.create(
                    user=user,
                    name=name,
                    period=period,
                    description=description,
                    method="center_analysis",
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

                for cl in cost_lines_data:
                    CostLine.objects.create(
                        scenario=sc,
                        label=cl['label'],
                        amount=Decimal(cl['amount']),
                        center=center_objs[cl['center_key']],
                        is_direct=False,
                        is_product=False,
                    )

                for alloc in allocations_data:
                    CostCenterAllocation.objects.create(
                        scenario=sc,
                        from_center=center_objs[alloc['from_key']],
                        to_center=center_objs[alloc['to_key']],
                        percentage=Decimal(str(alloc['percentage'])),
                    )

                for u in usages_data:
                    ProductCenterUsage.objects.create(
                        product=prod_objs[u['product_key']],
                        center=center_objs[u['center_key']],
                        units_used=Decimal(str(u['units_used'])),
                    )

                for month, pct in enumerate(seasonality, start=1):
                    SeasonalityEntry.objects.create(
                        scenario=sc, month=month, percentage=Decimal(str(pct)),
                    )

                return sc

            # ----------------------------------------------------------------
            # Helper : direct costing évolué
            # ----------------------------------------------------------------
            def make_advanced_scenario(name, preset, period, description, products_data,
                                       variable_costs, fixed_costs, seasonality):
                sc = CostScenario.objects.create(
                    user=user,
                    name=name,
                    period=period,
                    description=description,
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
            # Direct costing simple — Industriel
            # Plasturgie Dupont : fabrication de pièces plastiques
            # ----------------------------------------------------------------
            make_scenario(
                name='Plasturgie Dupont',
                preset='industriel',
                period='Annuel 2025',
                description='Direct costing — fabrication de pièces plastiques (boîtiers et joints).',
                products_data=[
                    {'key': 'p1', 'name': 'Boîtier série 100', 'quantity': 1500, 'unit_price': '12.00'},
                    {'key': 'p2', 'name': 'Joint d\'étanchéité', 'quantity': 3000, 'unit_price': '4.50'},
                ],
                variable_costs=[
                    {'name': 'Granulés plastique — Boîtier',  'category': 'Material', 'amount': '6500.00',  'product_key': 'p1'},
                    {'name': 'Colorants industriels — Boîtier','category': 'Material', 'amount': '1200.00',  'product_key': 'p1'},
                    {'name': 'Caoutchouc brut — Joint',        'category': 'Material', 'amount': '5500.00',  'product_key': 'p2'},
                    {'name': 'Énergie machines (partagée)',    'category': 'Overhead', 'amount': '2800.00'},
                ],
                fixed_costs=[
                    {'name': 'Loyer atelier de production', 'category': 'Rent',        'amount':  '9600.00'},
                    {'name': 'Salaires de production',      'category': 'Salary',      'amount': '36000.00'},
                    {'name': 'Amortissement presses',       'category': 'Depreciation','amount': '10000.00'},
                    {'name': 'Assurances industrielles',    'category': 'Other',       'amount':  '3200.00'},
                ],
                seasonality=[5, 5, 8, 9, 10, 12, 10, 10, 8, 7, 8, 8],
            )

            # ----------------------------------------------------------------
            # Direct costing simple — Commercial
            # Épicerie Figuier : vente de paniers et coffrets gastronomiques
            # ----------------------------------------------------------------
            make_scenario(
                name='Épicerie Figuier',
                preset='commercial',
                period='Annuel 2025',
                description='Direct costing — vente de paniers bio et coffrets dégustation.',
                products_data=[
                    {'key': 'p1', 'name': 'Panier bio prestige',   'quantity': 600, 'unit_price': '65.00'},
                    {'key': 'p2', 'name': 'Coffret dégustation',   'quantity': 400, 'unit_price': '48.00'},
                ],
                variable_costs=[
                    {'name': 'Achats produits bio — Panier',       'category': 'Material', 'amount': '22000.00', 'product_key': 'p1'},
                    {'name': 'Achats produits traiteur — Coffret', 'category': 'Material', 'amount': '12000.00', 'product_key': 'p2'},
                    {'name': 'Conditionnement & emballage',        'category': 'Material', 'amount':  '3500.00'},
                    {'name': 'Commissions représentants',          'category': 'Labor',    'amount':  '4000.00'},
                ],
                fixed_costs=[
                    {'name': 'Loyer boutique',           'category': 'Rent',   'amount': '18000.00'},
                    {'name': 'Salaires vendeurs',         'category': 'Salary', 'amount': '28000.00'},
                    {'name': 'Publicité & communication', 'category': 'Other',  'amount':  '5500.00'},
                    {'name': 'Assurances commerce',       'category': 'Other',  'amount':  '1800.00'},
                ],
                seasonality=[6, 6, 7, 8, 9, 10, 11, 10, 8, 7, 9, 9],
            )

            # ----------------------------------------------------------------
            # Direct costing simple — Services
            # Cabinet Nexus Conseil : missions de conseil et formations
            # ----------------------------------------------------------------
            make_scenario(
                name='Cabinet Nexus Conseil',
                preset='services',
                period='Annuel 2025',
                description='Direct costing — missions de conseil RH et formations en entreprise.',
                products_data=[
                    {'key': 'p1', 'name': 'Mission de conseil',     'quantity': 150, 'unit_price': '1200.00'},
                    {'key': 'p2', 'name': 'Formation en entreprise', 'quantity':  40, 'unit_price': '2500.00'},
                ],
                variable_costs=[
                    {'name': 'Déplacements & hébergement — Conseil',   'category': 'Overhead', 'amount':  '9000.00', 'product_key': 'p1'},
                    {'name': 'Intervenants externes — Formation',       'category': 'Labor',    'amount':  '7000.00', 'product_key': 'p2'},
                    {'name': 'Supports & ressources pédagogiques',     'category': 'Material', 'amount':  '2500.00'},
                ],
                fixed_costs=[
                    {'name': 'Salaires consultants permanents',  'category': 'Salary', 'amount': '68000.00'},
                    {'name': 'Loyer bureaux',                    'category': 'Rent',   'amount': '12000.00'},
                    {'name': 'Assurance responsabilité civile',  'category': 'Other',  'amount':  '2400.00'},
                    {'name': 'Frais informatiques & outils',     'category': 'Other',  'amount':  '4800.00'},
                ],
                seasonality=[7, 7, 8, 8, 9, 10, 10, 9, 8, 7, 7, 8],
            )

            # ----------------------------------------------------------------
            # Centres d'analyse — Industriel
            # Menuiserie Moreau : fenêtres PVC et portes bois
            # ----------------------------------------------------------------
            make_center_scenario(
                name='Menuiserie Moreau',
                preset='industriel',
                period='Annuel 2025',
                description=(
                    "Centres d'analyse — menuiserie industrielle. "
                    "Centres auxiliaires Entretien et Énergie répartis vers "
                    "Débit et Assemblage. Unités d'œuvre : h/machine et h/MOD."
                ),
                products_data=[
                    {'key': 'p1', 'name': 'Fenêtre PVC',  'quantity': 400, 'unit_price': '320.00'},
                    {'key': 'p2', 'name': 'Porte bois',   'quantity': 250, 'unit_price': '480.00'},
                ],
                centers_data=[
                    {'key': 'aux_entretien', 'code': 'ENT', 'name': 'Entretien',
                     'is_auxiliary': True,  'unit_of_work': '',              'total_units': 0},
                    {'key': 'aux_energie',   'code': 'ENE', 'name': 'Énergie',
                     'is_auxiliary': True,  'unit_of_work': '',              'total_units': 0},
                    {'key': 'debit',         'code': 'DEB', 'name': 'Centre Débit',
                     'is_auxiliary': False, 'unit_of_work': 'heure machine', 'total_units': 2000},
                    {'key': 'assemblage',    'code': 'ASM', 'name': 'Centre Assemblage',
                     'is_auxiliary': False, 'unit_of_work': 'heure MOD',     'total_units': 3000},
                ],
                cost_lines_data=[
                    {'label': 'Salaires entretien',        'amount': '18000.00', 'center_key': 'aux_entretien'},
                    {'label': 'Fournitures entretien',     'amount':  '4000.00', 'center_key': 'aux_entretien'},
                    {'label': 'Électricité',               'amount': '12000.00', 'center_key': 'aux_energie'},
                    {'label': 'Gaz industriel',            'amount':  '5000.00', 'center_key': 'aux_energie'},
                    {'label': 'Amortissement machines',    'amount': '24000.00', 'center_key': 'debit'},
                    {'label': 'Salaires opérateurs débit', 'amount': '36000.00', 'center_key': 'debit'},
                    {'label': 'Salaires monteurs',         'amount': '45000.00', 'center_key': 'assemblage'},
                    {'label': 'Outillage assemblage',      'amount':  '8000.00', 'center_key': 'assemblage'},
                ],
                allocations_data=[
                    {'from_key': 'aux_entretien', 'to_key': 'debit',      'percentage': 60},
                    {'from_key': 'aux_entretien', 'to_key': 'assemblage', 'percentage': 40},
                    {'from_key': 'aux_energie',   'to_key': 'debit',      'percentage': 70},
                    {'from_key': 'aux_energie',   'to_key': 'assemblage', 'percentage': 30},
                ],
                usages_data=[
                    {'product_key': 'p1', 'center_key': 'debit',      'units_used': 800},
                    {'product_key': 'p1', 'center_key': 'assemblage', 'units_used': 1200},
                    {'product_key': 'p2', 'center_key': 'debit',      'units_used': 1200},
                    {'product_key': 'p2', 'center_key': 'assemblage', 'units_used': 1800},
                ],
                seasonality=[5, 5, 8, 9, 10, 12, 10, 10, 8, 7, 8, 8],
            )

            # ----------------------------------------------------------------
            # Centres d'analyse — Services
            # Agence Créa Paris : campagnes web et identités visuelles
            # ----------------------------------------------------------------
            make_center_scenario(
                name='Agence Créa Paris',
                preset='services',
                period='Annuel 2025',
                description=(
                    "Centres d'analyse — agence de communication. "
                    "Centre auxiliaire Administration réparti vers Création, "
                    "Production et Conseil. Unités d'œuvre : h/créa, h/prod, mission."
                ),
                products_data=[
                    {'key': 'p1', 'name': 'Campagne web',      'quantity': 30, 'unit_price': '8500.00'},
                    {'key': 'p2', 'name': 'Identité visuelle', 'quantity': 20, 'unit_price': '5200.00'},
                ],
                centers_data=[
                    {'key': 'admin',      'code': 'ADM', 'name': 'Administration',
                     'is_auxiliary': True,  'unit_of_work': '',           'total_units': 0},
                    {'key': 'creation',   'code': 'CRE', 'name': 'Création',
                     'is_auxiliary': False, 'unit_of_work': 'heure créa', 'total_units': 1500},
                    {'key': 'production', 'code': 'PRO', 'name': 'Production',
                     'is_auxiliary': False, 'unit_of_work': 'heure prod', 'total_units': 800},
                    {'key': 'conseil',    'code': 'CON', 'name': 'Conseil',
                     'is_auxiliary': False, 'unit_of_work': 'mission',    'total_units': 50},
                ],
                cost_lines_data=[
                    {'label': 'Salaires administratifs',          'amount': '28000.00', 'center_key': 'admin'},
                    {'label': 'Loyer bureaux (quote-part admin)', 'amount':  '6000.00', 'center_key': 'admin'},
                    {'label': 'Salaires créatifs',                'amount': '55000.00', 'center_key': 'creation'},
                    {'label': 'Licences logiciels',               'amount':  '8000.00', 'center_key': 'creation'},
                    {'label': 'Salaires techniciens',             'amount': '32000.00', 'center_key': 'production'},
                    {'label': 'Matériel production',              'amount':  '5000.00', 'center_key': 'production'},
                    {'label': 'Salaires consultants',             'amount': '42000.00', 'center_key': 'conseil'},
                    {'label': 'Déplacements conseil',             'amount':  '4000.00', 'center_key': 'conseil'},
                ],
                allocations_data=[
                    {'from_key': 'admin', 'to_key': 'creation',   'percentage': 40},
                    {'from_key': 'admin', 'to_key': 'production', 'percentage': 30},
                    {'from_key': 'admin', 'to_key': 'conseil',    'percentage': 30},
                ],
                usages_data=[
                    {'product_key': 'p1', 'center_key': 'creation',   'units_used': 900},
                    {'product_key': 'p1', 'center_key': 'production', 'units_used': 500},
                    {'product_key': 'p1', 'center_key': 'conseil',    'units_used': 25},
                    {'product_key': 'p2', 'center_key': 'creation',   'units_used': 600},
                    {'product_key': 'p2', 'center_key': 'production', 'units_used': 300},
                    {'product_key': 'p2', 'center_key': 'conseil',    'units_used': 25},
                ],
                seasonality=[7, 7, 8, 8, 9, 10, 10, 9, 8, 7, 7, 8],
            )

            # ----------------------------------------------------------------
            # Centres d'analyse — Commercial
            # Logidis Distribution : produits entrée et milieu de gamme
            # ----------------------------------------------------------------
            make_center_scenario(
                name='Logidis Distribution',
                preset='commercial',
                period='Annuel 2025',
                description=(
                    "Centres d'analyse — distribution commerciale. "
                    "Centre auxiliaire Logistique réparti vers Réception, "
                    "Mise en rayon et Expédition. Unités d'œuvre : palette, h/travail, colis."
                ),
                products_data=[
                    {'key': 'p1', 'name': 'Produit entrée de gamme', 'quantity': 2000, 'unit_price': '25.00'},
                    {'key': 'p2', 'name': 'Produit milieu de gamme', 'quantity': 1200, 'unit_price': '45.00'},
                ],
                centers_data=[
                    {'key': 'logistique', 'code': 'LOG', 'name': 'Logistique commune',
                     'is_auxiliary': True,  'unit_of_work': '',               'total_units': 0},
                    {'key': 'reception',  'code': 'REC', 'name': 'Réception',
                     'is_auxiliary': False, 'unit_of_work': 'palette traitée','total_units': 500},
                    {'key': 'rayon',      'code': 'MRY', 'name': 'Mise en rayon',
                     'is_auxiliary': False, 'unit_of_work': 'heure travail',  'total_units': 1200},
                    {'key': 'expedition', 'code': 'EXP', 'name': 'Expédition',
                     'is_auxiliary': False, 'unit_of_work': 'colis expédié',  'total_units': 3200},
                ],
                cost_lines_data=[
                    {'label': 'Salaires logistique',    'amount': '20000.00', 'center_key': 'logistique'},
                    {'label': 'Assurances entrepôt',    'amount':  '5000.00', 'center_key': 'logistique'},
                    {'label': 'Salaires réception',     'amount': '18000.00', 'center_key': 'reception'},
                    {'label': 'Matériel manutention',   'amount':  '6000.00', 'center_key': 'reception'},
                    {'label': 'Salaires mise en rayon', 'amount': '22000.00', 'center_key': 'rayon'},
                    {'label': 'Fournitures rayon',      'amount':  '3000.00', 'center_key': 'rayon'},
                    {'label': 'Salaires expédition',    'amount': '28000.00', 'center_key': 'expedition'},
                    {'label': 'Emballages expédition',  'amount':  '8000.00', 'center_key': 'expedition'},
                ],
                allocations_data=[
                    {'from_key': 'logistique', 'to_key': 'reception',  'percentage': 30},
                    {'from_key': 'logistique', 'to_key': 'rayon',      'percentage': 40},
                    {'from_key': 'logistique', 'to_key': 'expedition', 'percentage': 30},
                ],
                usages_data=[
                    {'product_key': 'p1', 'center_key': 'reception',  'units_used': 200},
                    {'product_key': 'p1', 'center_key': 'rayon',      'units_used': 700},
                    {'product_key': 'p1', 'center_key': 'expedition', 'units_used': 2000},
                    {'product_key': 'p2', 'center_key': 'reception',  'units_used': 300},
                    {'product_key': 'p2', 'center_key': 'rayon',      'units_used': 500},
                    {'product_key': 'p2', 'center_key': 'expedition', 'units_used': 1200},
                ],
                seasonality=[6, 6, 7, 8, 9, 10, 11, 10, 8, 7, 9, 9],
            )

            # ----------------------------------------------------------------
            # Direct costing évolué — Industriel
            # Mécanique Leclerc : pièces usinées avec CF spécifiques par ligne
            # ----------------------------------------------------------------
            make_advanced_scenario(
                name='Mécanique Leclerc — Évolué',
                preset='industriel',
                period='Annuel 2025',
                description='Direct costing évolué — usinage de précision. CF spécifiques par ligne de production.',
                products_data=[
                    {'key': 'p1', 'name': 'Vilebrequin standard', 'quantity': 800, 'unit_price': '65.00'},
                    {'key': 'p2', 'name': 'Carter aluminium',     'quantity': 500, 'unit_price': '95.00'},
                ],
                variable_costs=[
                    {'name': 'Matières premières — Vilebrequin', 'category': 'Material', 'amount': '12000.00', 'product_key': 'p1'},
                    {'name': 'Main d\'œuvre directe — Vilebrequin','category': 'Labor',  'amount':  '8000.00', 'product_key': 'p1'},
                    {'name': 'Matières premières — Carter',       'category': 'Material', 'amount': '15000.00', 'product_key': 'p2'},
                    {'name': 'Main d\'œuvre directe — Carter',    'category': 'Labor',    'amount': '10000.00', 'product_key': 'p2'},
                    {'name': 'Énergie variable (partagée)',       'category': 'Overhead', 'amount':  '5000.00'},
                ],
                fixed_costs=[
                    {'name': 'Loyer usine',           'category': 'Rent',        'amount': '15000.00', 'is_common': True},
                    {'name': 'Salaires direction',    'category': 'Salary',      'amount': '42000.00', 'is_common': True},
                    {'name': 'Amort. bâtiment',       'category': 'Depreciation','amount':  '8000.00', 'is_common': True},
                    {'name': 'Amort. ligne Vilebrequin','category': 'Depreciation','amount':'18000.00', 'is_common': False, 'product_key': 'p1'},
                    {'name': 'Contrôle qualité Vilebrequin','category': 'Other', 'amount':  '6000.00', 'is_common': False, 'product_key': 'p1'},
                    {'name': 'Amort. ligne Carter',   'category': 'Depreciation','amount': '22000.00', 'is_common': False, 'product_key': 'p2'},
                ],
                seasonality=[5, 5, 8, 9, 10, 12, 10, 10, 8, 7, 8, 8],
            )

            # ----------------------------------------------------------------
            # Direct costing évolué — Commercial
            # Mode & Style : trois collections avec CF spécifiques de lancement
            # ----------------------------------------------------------------
            make_advanced_scenario(
                name='Mode & Style — Évolué',
                preset='commercial',
                period='Annuel 2025',
                description='Direct costing évolué — prêt-à-porter. CF de lancement spécifiques par collection.',
                products_data=[
                    {'key': 'p1', 'name': 'Collection Casual',   'quantity': 3000, 'unit_price': '18.00'},
                    {'key': 'p2', 'name': 'Collection Premium',  'quantity': 1500, 'unit_price': '32.00'},
                    {'key': 'p3', 'name': 'Accessoires luxe',    'quantity':  800, 'unit_price': '55.00'},
                ],
                variable_costs=[
                    {'name': 'Achats marchandises Casual',   'category': 'Material', 'amount': '32000.00', 'product_key': 'p1'},
                    {'name': 'Transport Casual',             'category': 'Overhead', 'amount':  '3000.00', 'product_key': 'p1'},
                    {'name': 'Achats marchandises Premium',  'category': 'Material', 'amount': '24000.00', 'product_key': 'p2'},
                    {'name': 'Transport Premium',            'category': 'Overhead', 'amount':  '2500.00', 'product_key': 'p2'},
                    {'name': 'Achats marchandises Accessoires','category': 'Material','amount': '20000.00', 'product_key': 'p3'},
                    {'name': 'Commission vente Accessoires', 'category': 'Labor',    'amount':  '4000.00', 'product_key': 'p3'},
                ],
                fixed_costs=[
                    {'name': 'Loyer boutique',               'category': 'Rent',   'amount': '24000.00', 'is_common': True},
                    {'name': 'Frais généraux',               'category': 'Other',  'amount':  '8000.00', 'is_common': True},
                    {'name': 'Salaires accueil',             'category': 'Salary', 'amount': '18000.00', 'is_common': True},
                    {'name': 'Publicité Collection Casual',  'category': 'Other',  'amount':  '5000.00', 'is_common': False, 'product_key': 'p1'},
                    {'name': 'SAV Collection Premium',       'category': 'Other',  'amount':  '3000.00', 'is_common': False, 'product_key': 'p2'},
                    {'name': 'Publicité Accessoires luxe',   'category': 'Other',  'amount':  '8000.00', 'is_common': False, 'product_key': 'p3'},
                ],
                seasonality=[6, 6, 7, 8, 9, 10, 11, 10, 8, 7, 9, 9],
            )

            # ----------------------------------------------------------------
            # Direct costing évolué — Services
            # Cabinet Formation Pro : audits et formations avec CF spécifiques
            # ----------------------------------------------------------------
            make_advanced_scenario(
                name='Cabinet Formation Pro — Évolué',
                preset='services',
                period='Annuel 2025',
                description='Direct costing évolué — conseil et formation. CF spécifiques : certification et location salle.',
                products_data=[
                    {'key': 'p1', 'name': 'Audit organisationnel', 'quantity': 80, 'unit_price': '1800.00'},
                    {'key': 'p2', 'name': 'Formation management',  'quantity': 60, 'unit_price': '1200.00'},
                ],
                variable_costs=[
                    {'name': 'Déplacements — Audit',          'category': 'Overhead', 'amount':  '8000.00', 'product_key': 'p1'},
                    {'name': 'Sous-traitance — Audit',        'category': 'Labor',    'amount': '12000.00', 'product_key': 'p1'},
                    {'name': 'Supports formation',            'category': 'Material', 'amount':  '4000.00', 'product_key': 'p2'},
                    {'name': 'Intervenants externes',         'category': 'Labor',    'amount':  '9000.00', 'product_key': 'p2'},
                ],
                fixed_costs=[
                    {'name': 'Salaires fixes',                'category': 'Salary', 'amount': '72000.00', 'is_common': True},
                    {'name': 'Loyer bureaux',                 'category': 'Rent',   'amount': '14400.00', 'is_common': True},
                    {'name': 'Assurance entreprise',          'category': 'Other',  'amount':  '3600.00', 'is_common': True},
                    {'name': 'Certification professionnelle — Audit','category': 'Other','amount':'5000.00','is_common': False, 'product_key': 'p1'},
                    {'name': 'Location salle de formation',  'category': 'Rent',   'amount':  '9000.00', 'is_common': False, 'product_key': 'p2'},
                ],
                seasonality=[7, 7, 8, 8, 9, 10, 10, 9, 8, 7, 7, 8],
            )

            # ----------------------------------------------------------------
            # Comparaison templates — même données, 3 presets différents
            # Atelier Sigma : illustration de l'impact du template sur l'affichage
            # Preset 1 : industriel  (×2)
            # Preset 2 : services    (×1)
            # ----------------------------------------------------------------
            SIGMA_PRODUCTS = [
                {'key': 'p1', 'name': 'Produit Alpha', 'quantity': 200, 'unit_price': '150.00'},
                {'key': 'p2', 'name': 'Produit Beta',  'quantity': 150, 'unit_price': '200.00'},
            ]
            SIGMA_VARIABLE = [
                {'name': 'Ressources — Alpha',          'category': 'Material', 'amount':  '8000.00', 'product_key': 'p1'},
                {'name': "Main d'œuvre — Alpha",        'category': 'Labor',    'amount':  '4500.00', 'product_key': 'p1'},
                {'name': 'Ressources — Beta',           'category': 'Material', 'amount':  '9000.00', 'product_key': 'p2'},
                {'name': "Main d'œuvre — Beta",         'category': 'Labor',    'amount':  '6000.00', 'product_key': 'p2'},
                {'name': 'Charges variables communes',  'category': 'Overhead', 'amount':  '3000.00'},
            ]
            SIGMA_FIXED = [
                {'name': 'Salaires permanents', 'category': 'Salary',      'amount': '48000.00', 'is_common': True},
                {'name': 'Loyer',               'category': 'Rent',        'amount': '10800.00', 'is_common': True},
                {'name': 'Assurances',          'category': 'Other',       'amount':  '2400.00', 'is_common': True},
                {'name': 'Équipement Alpha',    'category': 'Depreciation','amount': '12000.00', 'is_common': False, 'product_key': 'p1'},
                {'name': 'Équipement Beta',     'category': 'Depreciation','amount': '15000.00', 'is_common': False, 'product_key': 'p2'},
            ]
            SIGMA_SEASONALITY = [6, 6, 8, 9, 10, 11, 10, 9, 8, 7, 8, 8]

            for preset, label in [
                ('industriel', 'Industriel'),
                ('industriel', 'Industriel (v2)'),
                ('services',   'Services'),
            ]:
                make_advanced_scenario(
                    name=f'Atelier Sigma — {label}',
                    preset=preset,
                    period='Annuel 2025',
                    description=(
                        f'Scénario de comparaison templates — même données, preset {preset}. '
                        'Permet d\'observer l\'impact du template sur l\'affichage des résultats.'
                    ),
                    products_data=SIGMA_PRODUCTS,
                    variable_costs=SIGMA_VARIABLE,
                    fixed_costs=SIGMA_FIXED,
                    seasonality=SIGMA_SEASONALITY,
                )

            # ----------------------------------------------------------------
            # Comparaison templates bénéficiaire — même données, 2 presets
            # Atelier Côté Sud : résultat = +15 700 €
            # Objectif : montrer concrètement la différence d'affichage entre
            # le template industriel (stocks, CMP, saisonnalité) et services
            # (sans stocks ni CMP) sur un jeu de données identique rentable.
            # CA = 90 000 €  |  CV = 30 500 €  |  CF = 43 800 €
            # ----------------------------------------------------------------
            COTE_SUD_PRODUCTS = [
                {'key': 'p1', 'name': 'Prestation Alpha', 'quantity': 600, 'unit_price': '80.00'},
                {'key': 'p2', 'name': 'Prestation Beta',  'quantity': 350, 'unit_price': '120.00'},
            ]
            COTE_SUD_VARIABLE = [
                {'name': 'Ressources directes — Alpha', 'category': 'Material', 'amount': '15000.00', 'product_key': 'p1'},
                {'name': 'Ressources directes — Beta',  'category': 'Material', 'amount': '12000.00', 'product_key': 'p2'},
                {'name': 'Charges variables communes',  'category': 'Overhead', 'amount':  '3500.00'},
            ]
            COTE_SUD_FIXED = [
                {'name': 'Salaires permanents',         'category': 'Salary',      'amount': '24000.00', 'is_common': True},
                {'name': 'Loyer',                       'category': 'Rent',        'amount':  '9600.00', 'is_common': True},
                {'name': 'Amortissement équipements',   'category': 'Depreciation','amount':  '6000.00', 'is_common': True},
                {'name': 'Outillage spécifique — Alpha','category': 'Depreciation','amount':  '2400.00', 'is_common': False, 'product_key': 'p1'},
                {'name': 'Outillage spécifique — Beta', 'category': 'Depreciation','amount':  '1800.00', 'is_common': False, 'product_key': 'p2'},
            ]
            COTE_SUD_SEASONALITY = [5, 6, 9, 10, 11, 12, 10, 9, 8, 7, 7, 6]

            for preset, label in [
                ('industriel', 'Industriel'),
                ('services',   'Services'),
            ]:
                make_advanced_scenario(
                    name=f'Atelier Côté Sud — {label}',
                    preset=preset,
                    period='Annuel 2025',
                    description=(
                        f'Comparaison templates (preset {preset}) — résultat bénéficiaire +15 700 €. '
                        'Même données qu\'Atelier Côté Sud — '
                        + ('Services' if preset == 'industriel' else 'Industriel')
                        + '. Observer : stocks et CMP (industriel) vs affichage épuré (services).'
                    ),
                    products_data=COTE_SUD_PRODUCTS,
                    variable_costs=COTE_SUD_VARIABLE,
                    fixed_costs=COTE_SUD_FIXED,
                    seasonality=COTE_SUD_SEASONALITY,
                )

            self.stdout.write(self.style.SUCCESS(
                'Demo scenarios created and assigned to user "demo".\n'
                '  Direct costing simple:\n'
                '    - Plasturgie Dupont (industriel)\n'
                '    - Épicerie Figuier (commercial)\n'
                '    - Cabinet Nexus Conseil (services)\n'
                '  Centres d\'analyse:\n'
                '    - Menuiserie Moreau (industriel)\n'
                '    - Agence Créa Paris (services)\n'
                '    - Logidis Distribution (commercial)\n'
                '  Direct costing évolué:\n'
                '    - Mécanique Leclerc — Évolué (industriel)\n'
                '    - Mode & Style — Évolué (commercial)\n'
                '    - Cabinet Formation Pro — Évolué (services)\n'
                '  Comparaison templates (mêmes données, direct costing évolué):\n'
                '    - Atelier Sigma — Industriel (industriel)\n'
                '    - Atelier Sigma — Industriel (v2) (industriel)\n'
                '    - Atelier Sigma — Services (services)\n'
                '  Comparaison templates bénéficiaire (direct costing évolué, résultat +15 700 €):\n'
                '    - Atelier Côté Sud — Industriel (industriel)\n'
                '    - Atelier Côté Sud — Services (services)\n'
            ))
