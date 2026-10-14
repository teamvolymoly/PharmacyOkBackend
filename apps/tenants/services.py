from django.db import transaction

from .models import Tenant, TenantMembership


@transaction.atomic
def create_tenant_with_owner(*, name, slug, owner, owner_role):
    tenant = Tenant.objects.create(name=name, slug=slug)
    TenantMembership.objects.create(tenant=tenant, user=owner, role=owner_role)
    return tenant

