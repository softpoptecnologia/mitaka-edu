from django.db import migrations


def ensure_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for code, name in [
        ("SUPERADMIN", "Superadministrador"),
        ("SECRETARIA", "Secretaria Municipal"),
        ("TECNICO", "Técnico Pedagógico"),
        ("GESTOR", "Gestor Escolar"),
        ("COORDENADOR", "Coordenador Pedagógico"),
        ("PROFESSOR", "Professor"),
        ("AEE", "Atendimento Educacional Especializado"),
    ]:
        Role.objects.get_or_create(code=code, defaults={"name": name})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_accessibility_inclusive_phase"),
    ]

    operations = [
        migrations.RunPython(ensure_roles, noop),
    ]
