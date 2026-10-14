from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import ReferralCode, User
from apps.branches.models import Branch
from apps.roles.models import Role
from apps.tenants.models import Tenant, TenantMembership


class Command(BaseCommand):
    help = "Create or refresh the development-only PharmacyOK demo owner account."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="ajaygupta1427@gmail.com")
        parser.add_argument("--phone", default="7000795310")
        parser.add_argument("--password", default="ajay@100")

    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, "ALLOW_DEVELOPMENT_AUTH", False):
            raise CommandError("Development authentication helpers are disabled.")

        owner_role = Role.objects.filter(code="OWNER").first()
        if owner_role is None:
            raise CommandError("OWNER role is missing. Run migrations before seeding demo data.")

        user, created = User.objects.get_or_create(
            email=options["email"].strip().lower(),
            defaults={
                "phone": options["phone"],
                "first_name": "Ajay",
                "last_name": "Gupta",
                "is_active": True,
            },
        )
        user.phone = options["phone"]
        user.first_name = "Ajay"
        user.last_name = "Gupta"
        user.is_active = True
        user.set_password(options["password"])
        user.save()

        tenant, _ = Tenant.objects.get_or_create(
            slug="demo-pharmacy",
            defaults={"name": "Demo Pharmacy", "status": "ACTIVE"},
        )
        TenantMembership.objects.update_or_create(
            tenant=tenant,
            user=user,
            defaults={"role": owner_role, "status": "ACTIVE"},
        )
        Branch.objects.get_or_create(
            tenant=tenant,
            code="MAIN",
            defaults={
                "name": "Main Branch",
                "address_line_1": "Demo Address",
                "city": "New Delhi",
                "state": "Delhi",
                "postal_code": "110001",
                "country": "IN",
                "phone": options["phone"],
                "status": "ACTIVE",
            },
        )
        ReferralCode.objects.update_or_create(code="WELCOME100", defaults={"is_active": True})

        action = "Created" if created else "Refreshed"
        self.stdout.write(self.style.SUCCESS(f"{action} demo PharmacyOK account."))
        self.stdout.write(f"Mobile: {options['phone']}")
        self.stdout.write(f"Email: {user.email}")
        self.stdout.write(f"Password: {options['password']}")
        self.stdout.write(f"Reset OTP: {getattr(settings, 'PASSWORD_RESET_FIXED_OTP', '') or '(random)'}")
        self.stdout.write("Referral code: WELCOME100")
