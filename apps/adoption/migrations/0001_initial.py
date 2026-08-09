import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("curriculum", "0002_developmentdimension_practice_axis_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FormationProgram",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=200)),
                (
                    "audience",
                    models.CharField(
                        choices=[
                            ("professor", "Professoras e professores"),
                            ("coordenacao", "Coordenação pedagógica"),
                            ("gestao", "Equipe gestora escolar"),
                            ("tecnico", "Equipe técnica da Secretaria"),
                            ("familia", "Famílias acompanhadas pela rede"),
                        ],
                        max_length=20,
                    ),
                ),
                ("objective", models.TextField()),
                ("duration_hours", models.PositiveSmallIntegerField(default=4)),
                (
                    "modality",
                    models.CharField(
                        choices=[
                            ("presencial", "Presencial na escola / SME"),
                            ("hibrido", "Híbrido"),
                            ("ead", "A distância (PWA / tablet)"),
                        ],
                        default="hibrido",
                        max_length=20,
                    ),
                ),
                ("agenda", models.TextField(help_text="Um tópico por linha")),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "skill",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="formation_programs",
                        to="curriculum.skill",
                    ),
                ),
            ],
            options={
                "verbose_name": "Formação continuada",
                "verbose_name_plural": "Formações continuadas",
                "ordering": ["order", "title"],
            },
        ),
    ]
