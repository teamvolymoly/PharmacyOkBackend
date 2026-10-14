from uuid import UUID

from rest_framework.exceptions import PermissionDenied, ValidationError


def resolve_tenant_context(request, *, required=True):
    """Resolve tenant only through an authenticated user's active membership."""
    memberships = request.user.tenant_memberships.select_related(
        "tenant", "role"
    ).filter(status="ACTIVE", tenant__status="ACTIVE")

    requested_id = request.headers.get("X-Tenant-ID")
    if requested_id:
        try:
            requested_id = UUID(requested_id)
        except ValueError as exc:
            raise ValidationError({"X-Tenant-ID": "Must be a valid UUID."}) from exc
        membership = memberships.filter(tenant_id=requested_id).first()
        if membership is None:
            raise PermissionDenied("You do not have access to this tenant.")
    else:
        membership = memberships.order_by("created_at").first()

    if membership is None and required:
        raise PermissionDenied("No active tenant membership is available.")
    return membership


def validate_branch_access(membership, branch_id):
    if membership.role.code == "OWNER":
        branch = membership.tenant.branches.filter(id=branch_id, status="ACTIVE").first()
    else:
        branch = membership.accessible_branches.filter(
            branch_id=branch_id,
            branch__tenant=membership.tenant,
            branch__status="ACTIVE",
        ).values_list("branch", flat=True).first()
        if branch:
            branch = membership.tenant.branches.get(id=branch)
    if branch is None:
        raise PermissionDenied("You do not have access to this branch.")
    return branch

