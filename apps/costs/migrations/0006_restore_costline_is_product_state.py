from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("costs", "0005_remove_product_cost_categories"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="costline",
                    name="is_product",
                    field=models.BooleanField(default=False),
                ),
            ],
            database_operations=[],
        ),
    ]
