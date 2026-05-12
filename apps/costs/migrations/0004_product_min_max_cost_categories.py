from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("costs", "0003_costscenario_ui_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="max_cost_category",
            field=models.CharField(
                choices=[
                    ("variable_unit", "Coûts variables unitaires (matières, main d'oeuvre directe, commissions)"),
                    ("fixed_total", "Coûts fixes totaux (loyers, salaires fixes, amortissements)"),
                    ("sales_distribution", "Coûts commerciaux / distribution"),
                    ("specific", "Coûts spécifiques"),
                    ("indirect_centers", "Charges indirectes / centres"),
                ],
                default="fixed_total",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="min_cost_category",
            field=models.CharField(
                choices=[
                    ("variable_unit", "Coûts variables unitaires (matières, main d'oeuvre directe, commissions)"),
                    ("fixed_total", "Coûts fixes totaux (loyers, salaires fixes, amortissements)"),
                    ("sales_distribution", "Coûts commerciaux / distribution"),
                    ("specific", "Coûts spécifiques"),
                    ("indirect_centers", "Charges indirectes / centres"),
                ],
                default="variable_unit",
                max_length=30,
            ),
        ),
    ]
