from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.branches.models import Branch, MembershipBranchAccess
from apps.roles.models import Role
from apps.tenants.models import Tenant, TenantMembership


class TenantFoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="staff@example.com", password="StrongPass!234")
        self.role = Role.objects.create(code="TEST_MANAGER", name="Test Manager")
        self.tenant = Tenant.objects.create(name="ABC Pharmacy", slug="abc-pharmacy")
        self.membership = TenantMembership.objects.create(tenant=self.tenant, user=self.user, role=self.role)

    def test_tenant_creation(self):
        self.assertEqual(self.tenant.status, "ACTIVE")

    def test_membership_is_unique_per_tenant_and_user(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TenantMembership.objects.create(tenant=self.tenant, user=self.user, role=self.role)

    def test_branch_and_user_access_relationship(self):
        branch = Branch.objects.create(
            tenant=self.tenant, name="Neemuch", code="NMC", address_line_1="Main Road",
            city="Neemuch", state="Madhya Pradesh", postal_code="458441",
        )
        MembershipBranchAccess.objects.create(membership=self.membership, branch=branch)
        self.assertEqual(self.membership.accessible_branches.get().branch, branch)
        self.assertEqual(branch.tenant, self.tenant)

