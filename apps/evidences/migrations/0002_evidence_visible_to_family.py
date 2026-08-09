from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evidences", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="evidence",
            name="visible_to_family",
            field=models.BooleanField(
                default=False,
                help_text="Se marcado, a família pode ver esta evidência no portal (sem dados clínicos).",
            ),
        ),
    ]
