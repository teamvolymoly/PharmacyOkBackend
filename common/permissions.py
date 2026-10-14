from rest_framework.permissions import BasePermission

from common.tenancy import resolve_tenant_context


class HasTenantPermission(BasePermission):
    """Checks a view's `required_permission` against the resolved membership role."""

    message = "Your role does not grant this permission."

    def has_permission(self, request, view):
        membership = resolve_tenant_context(request)
        request.tenant_membership = membership
        request.tenant = membership.tenant
        required = getattr(view, "required_permission", None)
        if required is None or membership.role.code == "OWNER":
            return True
        return membership.role.permissions.filter(code=required).exists()

