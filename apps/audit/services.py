from .models import AuditLog


def record_audit_event(**event):
    return AuditLog.objects.create(**event)

