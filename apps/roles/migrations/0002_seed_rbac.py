from django.db import migrations

ROLES = ("OWNER", "ADMIN", "MANAGER", "PHARMACIST", "CASHIER", "INVENTORY_MANAGER", "ACCOUNTANT")
PERMISSIONS = (
    "sale.view", "sale.create", "sale.refund", "purchase.view", "purchase.create",
    "inventory.view", "inventory.adjust", "customer.view", "customer.manage",
    "report.view", "staff.view", "staff.manage", "settings.manage",
)


def seed(apps, schema_editor):
    Role = apps.get_model("roles", "Role")
    Permission = apps.get_model("roles", "Permission")
    permissions = []
    for code in PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(code=code, defaults={"name": code.replace(".", " ").title()})
        permissions.append(permission)
    for code in ROLES:
        role, _ = Role.objects.get_or_create(code=code, defaults={"name": code.replace("_", " ").title()})
        if code in ("OWNER", "ADMIN"):
            role.permissions.set(permissions)


def unseed(apps, schema_editor):
    apps.get_model("roles", "Role").objects.filter(code__in=ROLES).delete()
    apps.get_model("roles", "Permission").objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [("roles", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]

