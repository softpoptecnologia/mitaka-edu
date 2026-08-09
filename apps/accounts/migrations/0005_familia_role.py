from django.db import migrations


def ensure_familia(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.get_or_create(code="FAMILIA", defaults={"name": "Família / responsável"})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_bootstrap_roles"),
    ]

    operations = [
        migrations.RunPython(ensure_familia, noop),
    ]
