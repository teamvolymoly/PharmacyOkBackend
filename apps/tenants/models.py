from django.conf import settings
from django.db import models

from common.models import UUIDTimeStampedModel


class TenantStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    INACTIVE = "INACTIVE", "Inactive"


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INVITED = "INVITED", "Invited"
    SUSPENDED = "SUSPENDED", "Suspended"
    INACTIVE = "INACTIVE", "Inactive"


class Tenant(UUIDTimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=TenantStatus, default=TenantStatus.ACTIVE, db_index=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=TenantStatus.values),
                name="tenant_valid_status",
            )
        ]

    def __str__(self):
        return self.name


class TenantMembership(UUIDTimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenant_memberships")
    role = models.ForeignKey("roles.Role", on_delete=models.PROTECT, related_name="memberships")
    status = models.CharField(max_length=20, choices=MembershipStatus, default=MembershipStatus.ACTIVE, db_index=True)

    class Meta:
        ordering = ("tenant__name", "user__email")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "user"), name="unique_tenant_user_membership"),
            models.CheckConstraint(condition=models.Q(status__in=MembershipStatus.values), name="membership_valid_status"),
        ]
        indexes = [
            models.Index(fields=("tenant", "status"), name="membership_tenant_status_idx"),
            models.Index(fields=("user", "status"), name="membership_user_status_idx"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.tenant}"

