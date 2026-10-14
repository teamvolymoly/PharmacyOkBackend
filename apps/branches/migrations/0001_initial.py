import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("tenants", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="Branch",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=200)),
                ("code", models.CharField(max_length=50)),
                ("address_line_1", models.CharField(max_length=255)),
                ("address_line_2", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(max_length=100)),
                ("postal_code", models.CharField(max_length=20)),
                ("country", models.CharField(default="IN", max_length=2)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")], db_index=True, default="ACTIVE", max_length=20)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="branches", to="tenants.tenant")),
            ],
            options={
                "ordering": ("tenant", "name"),
                "indexes": [models.Index(fields=["tenant", "status"], name="branch_tenant_status_idx")],
                "constraints": [models.UniqueConstraint(fields=("tenant", "code"), name="unique_branch_code_per_tenant"), models.CheckConstraint(condition=models.Q(("status__in", ["ACTIVE", "INACTIVE"])), name="branch_valid_status")],
            },
        ),
        migrations.CreateModel(
            name="MembershipBranchAccess",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="membership_access", to="branches.branch")),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="accessible_branches", to="tenants.tenantmembership")),
            ],
            options={
                "indexes": [models.Index(fields=["membership", "branch"], name="membership_branch_idx")],
                "constraints": [models.UniqueConstraint(fields=("membership", "branch"), name="unique_membership_branch_access")],
            },
        ),
    ]

