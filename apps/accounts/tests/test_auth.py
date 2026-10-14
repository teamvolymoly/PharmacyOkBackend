from datetime import timedelta
from io import StringIO

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import (
    BlockedPhoneNumber,
    PasswordResetCode,
    ReferralCode,
    RegistrationCode,
    User,
)
from apps.accounts.views import generate_password_reset_code
from apps.branches.models import Branch
from apps.tenants.models import Tenant, TenantMembership


class UserAndAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="Owner@Example.COM",
            phone="+91 70007 95310",
            password="StrongPass!234",
        )

    def request_reset(self, **overrides):
        payload = {"mobile_number": "+917000795310", "email": "owner@example.com"}
        payload.update(overrides)
        return self.client.post(reverse("password-reset-request"), payload, format="json")

    def confirm_reset(self, **overrides):
        payload = {
            "mobile_number": "+917000795310",
            "email": "owner@example.com",
            "otp": "4562",
            "new_password": "NewPass123!",
        }
        payload.update(overrides)
        return self.client.post(reverse("password-reset-confirm"), payload, format="json")

    def test_user_creation_normalizes_email_and_hashes_password(self):
        self.assertEqual(self.user.email, "owner@example.com")
        self.assertNotEqual(self.user.password, "StrongPass!234")
        self.assertTrue(self.user.check_password("StrongPass!234"))

    def test_login_returns_token_pair(self):
        response = self.client.post(reverse("login"), {"email": "owner@example.com", "password": "StrongPass!234"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_accepts_mobile_number(self):
        response = self.client.post(
            reverse("login"),
            {"mobile_number": "7000795310", "password": "StrongPass!234"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_accepts_mobile_number_with_country_code(self):
        response = self.client.post(
            reverse("login"),
            {"mobile_number": "+917000795310", "password": "StrongPass!234"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            reverse("login"),
            {"mobile_number": "7000795310", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_rejects_unknown_or_missing_mobile(self):
        unknown = self.client.post(
            reverse("login"),
            {"mobile_number": "9999999999", "password": "StrongPass!234"},
            format="json",
        )
        missing = self.client.post(reverse("login"), {"password": "StrongPass!234"}, format="json")
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(missing.status_code, 401)

    def test_login_rejects_inactive_account(self):
        self.user.is_active = False
        self.user.save(update_fields=("is_active", "updated_at"))
        response = self.client.post(
            reverse("login"),
            {"mobile_number": "7000795310", "password": "StrongPass!234"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_rejects_ambiguous_normalized_mobile(self):
        User.objects.create_user(
            email="duplicate@example.com",
            phone="7000795310",
            password="StrongPass!234",
        )
        response = self.client.post(
            reverse("login"),
            {"mobile_number": "+917000795310", "password": "StrongPass!234"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_password_reset_sends_otp_and_updates_password(self):
        request_response = self.request_reset()
        self.assertEqual(request_response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("4562", mail.outbox[0].body)

        confirm_response = self.confirm_reset()
        self.assertEqual(confirm_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass123!"))

    def test_password_reset_rejects_invalid_otp(self):
        self.request_reset()
        response = self.confirm_reset(otp="0000")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Invalid OTP")

    def test_password_reset_rejects_unknown_mobile_and_mismatched_email(self):
        unknown = self.request_reset(mobile_number="9999999999")
        mismatched = self.request_reset(email="someone@example.com")
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(mismatched.status_code, 400)

    def test_password_reset_rejects_malformed_contact_values(self):
        malformed_email = self.request_reset(email="not-an-email")
        missing_mobile = self.request_reset(mobile_number="")
        self.assertEqual(malformed_email.status_code, 400)
        self.assertEqual(missing_mobile.status_code, 400)

    def test_password_reset_email_match_is_case_insensitive(self):
        response = self.request_reset(email="OWNER@EXAMPLE.COM")
        self.assertEqual(response.status_code, 200)

    def test_password_reset_resend_invalidates_previous_code(self):
        self.request_reset()
        first_code = PasswordResetCode.objects.get()
        self.request_reset()
        first_code.refresh_from_db()
        self.assertIsNotNone(first_code.used_at)
        self.assertEqual(PasswordResetCode.objects.filter(used_at__isnull=True).count(), 1)

    def test_password_reset_request_is_rate_limited(self):
        self.assertEqual(self.request_reset().status_code, 200)
        self.assertEqual(self.request_reset().status_code, 200)
        self.assertEqual(self.request_reset().status_code, 200)
        self.assertEqual(self.request_reset().status_code, 429)

    def test_password_reset_rejects_expired_otp(self):
        self.request_reset()
        PasswordResetCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.confirm_reset()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Invalid OTP")

    def test_password_reset_locks_code_after_five_failures(self):
        self.request_reset()
        for _ in range(5):
            self.assertEqual(self.confirm_reset(otp="0000").status_code, 400)
        self.assertEqual(self.confirm_reset().status_code, 400)

    def test_password_reset_rejects_invalid_otp_format_and_short_password(self):
        self.request_reset()
        bad_otp = self.confirm_reset(otp="12ab")
        short_password = self.confirm_reset(new_password="12345")
        self.assertEqual(bad_otp.status_code, 400)
        self.assertEqual(short_password.status_code, 400)

    def test_password_reset_code_is_single_use(self):
        self.request_reset()
        self.assertEqual(self.confirm_reset().status_code, 200)
        self.assertEqual(self.confirm_reset(new_password="AnotherPass123!").status_code, 400)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 401)


class DemoAccountCommandTests(TestCase):
    def test_seed_demo_account_is_idempotent_and_complete(self):
        output = StringIO()
        call_command("seed_demo_account", stdout=output)
        call_command("seed_demo_account", stdout=output)

        user = User.objects.get(email="ajaygupta1427@gmail.com")
        self.assertEqual(user.phone, "7000795310")
        self.assertTrue(user.check_password("ajay@100"))
        self.assertEqual(Tenant.objects.filter(slug="demo-pharmacy").count(), 1)
        self.assertEqual(TenantMembership.objects.filter(user=user, status="ACTIVE").count(), 1)
        self.assertEqual(Branch.objects.filter(tenant__slug="demo-pharmacy", code="MAIN").count(), 1)
        self.assertTrue(ReferralCode.objects.get(code="WELCOME100").is_active)
        self.assertIn("Reset OTP: 4562", output.getvalue())

    @override_settings(ALLOW_DEVELOPMENT_AUTH=False)
    def test_seed_demo_account_is_blocked_without_development_auth(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo_account")

    @override_settings(ALLOW_DEVELOPMENT_AUTH=False, PASSWORD_RESET_FIXED_OTP="4562")
    def test_fixed_otp_is_blocked_without_development_auth(self):
        with self.assertRaises(ImproperlyConfigured):
            generate_password_reset_code()


class RegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.details = {
            "pharmacy_name": "Jai Shree Mahakal Pharmacy",
            "mobile_number": "6265880144",
            "email": "rochakmalviya@gmail.com",
            "postal_code": "452001",
        }

    def request_registration(self, **overrides):
        payload = {**self.details, **overrides}
        return self.client.post(reverse("register-request"), payload, format="json")

    def confirm_registration(self, registration_id, **overrides):
        payload = {
            "registration_id": registration_id,
            "otp": "4562",
            "password": "rochak@45",
            "referral_code": "",
        }
        payload.update(overrides)
        return self.client.post(reverse("register-confirm"), payload, format="json")

    def test_registration_creates_complete_owner_workspace(self):
        request_response = self.request_registration()
        self.assertEqual(request_response.status_code, 200)
        self.assertIn("4562", mail.outbox[0].body)

        response = self.confirm_registration(request_response.data["registration_id"])
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email=self.details["email"])
        self.assertTrue(user.check_password("rochak@45"))
        membership = TenantMembership.objects.get(user=user)
        self.assertEqual(membership.role.code, "OWNER")
        self.assertTrue(Branch.objects.filter(tenant=membership.tenant, code="MAIN", postal_code="452001").exists())

    def test_registration_accepts_country_code(self):
        response = self.request_registration(mobile_number="+916265880144")
        self.assertEqual(response.status_code, 200)
        registration = RegistrationCode.objects.get(id=response.data["registration_id"])
        self.assertEqual(registration.phone, "6265880144")

    def test_registration_validates_all_initial_fields(self):
        cases = (
            ({"pharmacy_name": ""}, "pharmacy_name"),
            ({"mobile_number": "62658"}, "mobile_number"),
            ({"email": "invalid"}, "email"),
            ({"postal_code": "45200"}, "postal_code"),
        )
        for override, field in cases:
            with self.subTest(field=field):
                response = self.request_registration(**override)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data["error"]["details"])

    def test_registration_rejects_existing_email_and_phone(self):
        User.objects.create_user(email="existing@example.com", phone="9999999999", password="password")
        email_response = self.request_registration(email="existing@example.com")
        phone_response = self.request_registration(mobile_number="+919999999999")
        self.assertEqual(email_response.status_code, 400)
        self.assertEqual(phone_response.status_code, 400)

    def test_registration_rejects_blocked_phone(self):
        BlockedPhoneNumber.objects.create(phone="6265880144", reason="Test block")
        response = self.request_registration()
        self.assertEqual(response.status_code, 400)
        self.assertIn("blocked", response.data["error"]["details"]["detail"][0].lower())

    def test_registration_request_is_rate_limited_and_invalidates_prior_code(self):
        first = self.request_registration()
        second = self.request_registration()
        first_code = RegistrationCode.objects.get(id=first.data["registration_id"])
        first_code.refresh_from_db()
        self.assertIsNotNone(first_code.completed_at)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.request_registration().status_code, 200)
        self.assertEqual(self.request_registration().status_code, 429)

    def test_registration_rejects_invalid_expired_and_reused_otp(self):
        request_response = self.request_registration()
        registration_id = request_response.data["registration_id"]
        self.assertEqual(self.confirm_registration(registration_id, otp="0000").status_code, 400)
        RegistrationCode.objects.filter(id=registration_id).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.confirm_registration(registration_id).status_code, 400)

        fresh = self.request_registration(email="second@example.com", mobile_number="6265880145")
        fresh_id = fresh.data["registration_id"]
        self.assertEqual(self.confirm_registration(fresh_id).status_code, 201)
        self.assertEqual(self.confirm_registration(fresh_id).status_code, 400)

    def test_registration_locks_otp_after_five_failures(self):
        registration_id = self.request_registration().data["registration_id"]
        for _ in range(5):
            self.assertEqual(self.confirm_registration(registration_id, otp="0000").status_code, 400)
        self.assertEqual(self.confirm_registration(registration_id).status_code, 400)

    def test_registration_validates_password_and_referral_code(self):
        registration_id = self.request_registration().data["registration_id"]
        self.assertEqual(self.confirm_registration(registration_id, password="12345").status_code, 400)
        self.assertEqual(self.confirm_registration(registration_id, referral_code="NOPE").status_code, 400)
        ReferralCode.objects.create(code="WELCOME100")
        self.assertEqual(self.confirm_registration(registration_id, referral_code="welcome100").status_code, 201)

    def test_registration_rejects_unknown_request_id_and_malformed_otp(self):
        missing = self.confirm_registration("00000000-0000-0000-0000-000000000000")
        registration_id = self.request_registration().data["registration_id"]
        malformed = self.confirm_registration(registration_id, otp="90x")
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(malformed.status_code, 400)

