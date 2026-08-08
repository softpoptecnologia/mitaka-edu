from django.db import migrations


def ensure_features(apps, schema_editor):
    Category = apps.get_model("accessibility", "AccessibilityCategory")
    Feature = apps.get_model("accessibility", "AccessibilityFeature")
    order_map = {
        "VISUAL": 10,
        "AUDITORY": 20,
        "MOTOR": 30,
        "COGNITIVE": 40,
        "SENSORY": 50,
        "COMMUNICATION": 60,
    }
    names = dict(Category._meta.get_field("code").choices)
    categories = {}
    for code, label in names.items():
        cat, _ = Category.objects.update_or_create(
            code=code, defaults={"name": label, "order": order_map.get(code, 99)}
        )
        categories[code] = cat
    specs = [
        ("VISUAL", "VISUAL_SCREEN_READER", "Leitor de tela", "a11y-screen-reader", 10),
        ("VISUAL", "VISUAL_HIGH_CONTRAST", "Alto contraste", "a11y-high-contrast", 20),
        ("VISUAL", "VISUAL_LARGE_TEXT", "Texto ampliado", "a11y-large-text", 30),
        ("AUDITORY", "AUDITORY_CAPTIONS", "Legendas", "", 10),
        ("AUDITORY", "AUDITORY_VISUAL_INSTRUCTION", "Instrução visual", "", 20),
        ("AUDITORY", "AUDITORY_LIBRAS", "Libras", "", 30),
        ("MOTOR", "MOTOR_LARGE_TARGET", "Alvos ampliados", "a11y-large-target", 10),
        ("MOTOR", "MOTOR_KEYBOARD", "Navegação por teclado", "", 20),
        ("MOTOR", "MOTOR_NO_DRAG", "Sem arrastar e soltar", "", 30),
        ("COGNITIVE", "COGNITIVE_SHORT_INSTRUCTIONS", "Instruções curtas", "", 10),
        ("COGNITIVE", "COGNITIVE_EXTRA_TIME", "Tempo ampliado", "", 20),
        ("COGNITIVE", "COGNITIVE_STEP_BY_STEP", "Instruções passo a passo", "a11y-step-by-step", 30),
        ("COGNITIVE", "COGNITIVE_NO_TIME_LIMIT", "Sem limite rígido de tempo", "", 40),
        ("COGNITIVE", "COGNITIVE_REPEAT_INSTRUCTIONS", "Repetição de instruções", "", 50),
        ("SENSORY", "SENSORY_REDUCED_MOTION", "Redução de animações", "a11y-reduced-motion", 10),
        ("SENSORY", "SENSORY_REDUCED_STIMULUS", "Redução de estímulos", "a11y-reduced-stimulus", 20),
    ]
    for cat_code, feat_code, name, css_class, order in specs:
        Feature.objects.update_or_create(
            code=feat_code,
            defaults={
                "category": categories[cat_code],
                "name": name,
                "css_class": css_class,
                "order": order,
                "is_active": True,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accessibility", "0001_accessibility_inclusive_phase"),
    ]

    operations = [
        migrations.RunPython(ensure_features, noop),
    ]
