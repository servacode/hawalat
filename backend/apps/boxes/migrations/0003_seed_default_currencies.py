"""زرع العملات الافتراضية المتفق عليها (دولار/يورو/تركي/سوري) للمستأجرين الحاليين."""

from django.db import migrations

DEFAULT_CURRENCIES = [
    ("USD", "دولار أمريكي"),
    ("EUR", "يورو"),
    ("TRY", "ليرة تركية"),
    ("SYP", "ليرة سورية"),
]


def seed(apps, schema_editor):
    Tenant = apps.get_model("core", "Tenant")
    Currency = apps.get_model("boxes", "Currency")
    for tenant in Tenant.objects.all():
        for code, name in DEFAULT_CURRENCIES:
            Currency.objects.get_or_create(tenant=tenant, code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [
        ("boxes", "0002_reconciliation"),
        ("core", "0001_initial"),
    ]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
