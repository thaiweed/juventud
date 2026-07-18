import uuid
from django.db import migrations, models


def generate_unique_public_ids(apps, schema_editor):
    """Assign unique UUIDs to all existing Order rows."""
    Order = apps.get_model('orders', 'Order')
    for order in Order.objects.filter(public_id__isnull=True):
        order.public_id = uuid.uuid4()
        order.save(update_fields=['public_id'])


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_orderitem_color_orderitem_size"),
    ]

    operations = [
        # Step 1: Add public_id as nullable so existing rows don't conflict
        migrations.AddField(
            model_name="order",
            name="public_id",
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                help_text="Public-facing UUID — safe to expose in URLs/emails",
            ),
        ),
        # Step 2: Populate unique UUIDs for all existing rows
        migrations.RunPython(
            generate_unique_public_ids,
            reverse_code=migrations.RunPython.noop,
        ),
        # Step 3: Make it non-nullable and unique
        migrations.AlterField(
            model_name="order",
            name="public_id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                help_text="Public-facing UUID — safe to expose in URLs/emails",
            ),
        ),
        # Step 4: Add session_key
        migrations.AddField(
            model_name="order",
            name="session_key",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Django session key at order creation time",
                max_length=40,
            ),
        ),
    ]
