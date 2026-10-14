from django.core.exceptions import ValidationError
from django.db import models

from common.models import UUIDTimeStampedModel


class BranchStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class Branch(UUIDTimeStampedModel):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2, default="IN")
    phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=20, choices=BranchStatus, default=BranchStatus.ACTIVE, db_index=True)

    class Meta:
        ordering = ("tenant", "name")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "code"), name="unique_branch_code_per_tenant"),
            models.CheckConstraint(condition=models.Q(status__in=BranchStatus.values), name="branch_valid_status"),
        ]
        indexes = [models.Index(fields=("tenant", "status"), name="branch_tenant_status_idx")]

    def __str__(self):
        return f"{self.tenant}: {self.name}"


class MembershipBranchAccess(UUIDTimeStampedModel):
    membership = models.ForeignKey("tenants.TenantMembership", on_delete=models.CASCADE, related_name="accessible_branches")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="membership_access")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("membership", "branch"), name="unique_membership_branch_access")]
        indexes = [models.Index(fields=("membership", "branch"), name="membership_branch_idx")]

    def clean(self):
        if self.membership_id and self.branch_id and self.membership.tenant_id != self.branch.tenant_id:
            raise ValidationError("Membership and branch must belong to the same tenant.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

