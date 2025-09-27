from django.db import migrations, models
import django.db.models.deletion
import uuid

def migrate_category_data(apps, schema_editor):
    Budget = apps.get_model("budgets", "Budget")
    Category = apps.get_model("budgets", "Category")

    # Create categories for distinct strings
    category_map = {}
    for cat_name in Budget.objects.values_list("category", flat=True).distinct():
        category, _ = Category.objects.get_or_create(
            name=cat_name,
            defaults={"id": uuid.uuid4(), "icon": "💰"}
        )
        category_map[cat_name] = category

    # Assign FK values
    for budget in Budget.objects.all():
        if budget.category in category_map:
            budget.category_fk = category_map[budget.category]
            budget.save(update_fields=["category_fk"])

class Migration(migrations.Migration):
    dependencies = [
        ("budgets", "0002_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="budget",
            name="category_fk",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="budgets.category",
                related_name="budget_set",
            ),
        ),
        migrations.RunPython(migrate_category_data, reverse_code=migrations.RunPython.noop),
    ]
