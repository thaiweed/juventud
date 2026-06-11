from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_productimage_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="has_multiple_colors",
            field=models.BooleanField(default=False, verbose_name="Несколько цветов"),
        ),
    ]
