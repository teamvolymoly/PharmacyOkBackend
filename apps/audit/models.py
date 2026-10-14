from django.conf import settings
from django.db import models

from common.models import UUIDTimeStampedModel


class AuditLog(UUIDTimeStampedModel):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="audit_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="audit_logs")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("tenant", "created_at"), name="audit_tenant_created_idx"),
            models.Index(fields=("tenant", "entity_type", "entity_id"), name="audit_entity_idx"),
            models.Index(fields=("user", "created_at"), name="audit_user_created_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit logs are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit logs cannot be deleted through the application.")

