import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.branches.models import Branch
from apps.roles.models import Role
from apps.tenants.models import Tenant, TenantMembership

from .models import PasswordResetCode, RegistrationCode, User
from .serializers import (
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationConfirmSerializer,
    RegistrationRequestSerializer,
)


def generate_password_reset_code():
    fixed_code = getattr(settings, "PASSWORD_RESET_FIXED_OTP", "")
    if fixed_code:
        if not getattr(settings, "ALLOW_DEVELOPMENT_AUTH", False):
            raise ImproperlyConfigured("Fixed password-reset OTPs are development-only.")
        return fixed_code
    return f"{secrets.randbelow(10_000):04d}"


class LoginView(TokenObtainPairView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer


class PasswordResetRequestView(GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        recent_codes = PasswordResetCode.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(minutes=1),
        ).count()
        if recent_codes >= 3:
            return Response({"detail": "Please wait before requesting another OTP."}, status=429)

        code = generate_password_reset_code()
        with transaction.atomic():
            PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
            PasswordResetCode.objects.create(
                user=user,
                code_hash=make_password(code),
                expires_at=timezone.now() + timedelta(minutes=10),
            )

        send_mail(
            "Your PharmacyOK password reset code",
            f"Your PharmacyOK verification code is {code}. It expires in 10 minutes.",
            getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pharmacyok.com"),
            [user.email],
            fail_silently=False,
        )
        return Response({"detail": "OTP sent to your email."})


class PasswordResetConfirmView(GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        reset_code = PasswordResetCode.objects.filter(
            user=user,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
            failed_attempts__lt=5,
        ).first()
        if reset_code is None or not check_password(serializer.validated_data["otp"], reset_code.code_hash):
            if reset_code is not None:
                reset_code.failed_attempts += 1
                reset_code.save(update_fields=("failed_attempts", "updated_at"))
            return Response({"detail": "Invalid OTP"}, status=400)

        with transaction.atomic():
            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=("password", "updated_at"))
            reset_code.used_at = timezone.now()
            reset_code.save(update_fields=("used_at", "updated_at"))
        return Response({"detail": "Password reset successfully."})


class RegistrationRequestView(GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RegistrationRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        recent = RegistrationCode.objects.filter(
            phone=data["normalized_phone"],
            created_at__gte=timezone.now() - timedelta(minutes=1),
        ).count()
        if recent >= 3:
            return Response({"detail": "Please wait before requesting another OTP."}, status=429)

        code = generate_password_reset_code()
        RegistrationCode.objects.filter(
            phone=data["normalized_phone"], completed_at__isnull=True
        ).update(completed_at=timezone.now())
        registration = RegistrationCode.objects.create(
            pharmacy_name=data["pharmacy_name"].strip(),
            phone=data["normalized_phone"],
            email=data["email"].strip().lower(),
            postal_code=data["postal_code"],
            code_hash=make_password(code),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        send_mail(
            "Your PharmacyOK registration code",
            f"Your PharmacyOK registration code is {code}. It expires in 10 minutes.",
            getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pharmacyok.com"),
            [registration.email],
            fail_silently=False,
        )
        return Response({"registration_id": str(registration.id), "detail": "OTP sent successfully."})


class RegistrationConfirmView(GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RegistrationConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = serializer.validated_data["registration"]
        if (
            registration.completed_at is not None
            or registration.expires_at <= timezone.now()
            or registration.failed_attempts >= 5
            or not check_password(serializer.validated_data["otp"], registration.code_hash)
        ):
            if registration.completed_at is None and registration.failed_attempts < 5:
                registration.failed_attempts += 1
                registration.save(update_fields=("failed_attempts", "updated_at"))
            return Response({"detail": "Invalid OTP"}, status=400)

        if User.objects.filter(email__iexact=registration.email).exists():
            return Response({"detail": "An account with this email already exists."}, status=409)

        owner_role = Role.objects.get(code="OWNER")
        with transaction.atomic():
            user = User.objects.create_user(
                email=registration.email,
                phone=registration.phone,
                password=serializer.validated_data["password"],
            )
            tenant = Tenant.objects.create(
                name=registration.pharmacy_name,
                slug=f"pharmacy-{user.id.hex[:12]}",
                status="ACTIVE",
            )
            TenantMembership.objects.create(tenant=tenant, user=user, role=owner_role, status="ACTIVE")
            Branch.objects.create(
                tenant=tenant,
                name="Main Branch",
                code="MAIN",
                address_line_1="To be updated",
                city="",
                state="",
                postal_code=registration.postal_code,
                country="IN",
                phone=registration.phone,
                status="ACTIVE",
            )
            registration.completed_at = timezone.now()
            registration.save(update_fields=("completed_at", "updated_at"))
        return Response({"detail": "Registration completed successfully."}, status=201)


class RefreshView(GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = TokenRefreshSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class LogoutView(GenericAPIView):
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = serializer.validated_data["refresh"]
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response({"refresh": ["Invalid or expired token."]}, status=400)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user

    def get(self, request):
        return self.retrieve(request)

