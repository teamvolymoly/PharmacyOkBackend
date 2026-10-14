import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("roles", "0002_seed_rbac"),
    ]
    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("SUSPENDED", "Suspended"), ("INACTIVE", "Inactive")], db_index=True, default="ACTIVE", max_length=20)),
            ],
            options={"ordering": ("name",), "constraints": [models.CheckConstraint(condition=models.Q(("status__in", ["ACTIVE", "SUSPENDED", "INACTIVE"])), name="tenant_valid_status")]},
        ),
        migrations.CreateModel(
            name="TenantMembership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("INVITED", "Invited"), ("SUSPENDED", "Suspended"), ("INACTIVE", "Inactive")], db_index=True, default="ACTIVE", max_length=20)),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memberships", to="roles.role")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="tenants.tenant")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tenant_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("tenant__name", "user__email"),
                "indexes": [models.Index(fields=["tenant", "status"], name="membership_tenant_status_idx"), models.Index(fields=["user", "status"], name="membership_user_status_idx")],
                "constraints": [models.UniqueConstraint(fields=("tenant", "user"), name="unique_tenant_user_membership"), models.CheckConstraint(condition=models.Q(("status__in", ["ACTIVE", "INVITED", "SUSPENDED", "INACTIVE"])), name="membership_valid_status")],
            },
        ),
    ]

