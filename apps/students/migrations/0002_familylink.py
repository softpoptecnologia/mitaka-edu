import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FamilyLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                (
                    "kinship",
                    models.CharField(
                        choices=[
                            ("mae", "Mãe"),
                            ("pai", "Pai"),
                            ("avo", "Avó/Avô"),
                            ("responsavel", "Responsável"),
                            ("outro", "Outro"),
                        ],
                        default="responsavel",
                        max_length=20,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="family_links",
                        to="students.student",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="family_links",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Vínculo familiar",
                "verbose_name_plural": "Vínculos familiares",
                "ordering": ["student__full_name"],
                "unique_together": {("user", "student")},
            },
        ),
    ]
