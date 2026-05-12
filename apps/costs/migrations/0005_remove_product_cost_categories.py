from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("costs", "0004_product_min_max_cost_categories"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="max_cost_category",
        ),
        migrations.RemoveField(
            model_name="product",
            name="min_cost_category",
        ),
    ]
