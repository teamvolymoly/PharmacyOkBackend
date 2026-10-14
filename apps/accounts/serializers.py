import re

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema_field

from common.tenancy import resolve_tenant_context

from .models import BlockedPhoneNumber, ReferralCode, RegistrationCode, User


def normalize_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    return digits


def user_for_mobile(mobile_number):
    normalized = normalize_phone(mobile_number)
    matches = [
        user
        for user in User.objects.filter(is_active=True).exclude(phone="").only("id", "email", "phone")
        if normalize_phone(user.phone) == normalized
    ]
    return matches[0] if len(matches) == 1 else None


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone")


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD
    mobile_number = serializers.CharField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = False

    @staticmethod
    def _normalized_phone(value):
        return normalize_phone(value)

    def validate(self, attrs):
        mobile_number = attrs.pop("mobile_number", "")
        if mobile_number:
            normalized = self._normalized_phone(mobile_number)
            matching_users = [
                user
                for user in User.objects.exclude(phone="").only("email", "phone")
                if self._normalized_phone(user.phone) == normalized
            ]
            if len(matching_users) != 1:
                raise AuthenticationFailed("No active account found with the given credentials")
            attrs[self.username_field] = matching_users[0].email
        elif not attrs.get(self.username_field):
            raise AuthenticationFailed("Enter a mobile number and password")

        return super().validate(attrs)


class PasswordResetRequestSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=16)
    email = serializers.EmailField()

    def validate(self, attrs):
        user = user_for_mobile(attrs["mobile_number"])
        if user is None:
            raise serializers.ValidationError({"mobile_number": "Invalid mobile number"})
        if user.email.casefold() != attrs["email"].strip().casefold():
            raise serializers.ValidationError({
                "detail": "Invalid email. Enter your registered or recovery email to receive the verification code."
            })
        attrs["user"] = user
        return attrs


class PasswordResetConfirmSerializer(PasswordResetRequestSerializer):
    otp = serializers.RegexField(r"^\d{4}$")
    new_password = serializers.CharField(min_length=6, max_length=128, write_only=True)


class RegistrationRequestSerializer(serializers.Serializer):
    pharmacy_name = serializers.CharField(max_length=200)
    mobile_number = serializers.RegexField(r"^\+?\d{10,15}$", max_length=16)
    email = serializers.EmailField()
    postal_code = serializers.RegexField(r"^\d{6}$")

    def validate(self, attrs):
        phone = normalize_phone(attrs["mobile_number"])
        if BlockedPhoneNumber.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({
                "detail": "Your mobile number is blocked. Please contact our support team at 7000795310 to proceed."
            })
        if User.objects.filter(email__iexact=attrs["email"].strip()).exists():
            raise serializers.ValidationError({"email": "An account with this email already exists"})
        if any(normalize_phone(value) == phone for value in User.objects.exclude(phone="").values_list("phone", flat=True)):
            raise serializers.ValidationError({"mobile_number": "An account with this mobile number already exists"})
        attrs["normalized_phone"] = phone
        return attrs


class RegistrationConfirmSerializer(serializers.Serializer):
    registration_id = serializers.PrimaryKeyRelatedField(
        queryset=RegistrationCode.objects.all(), source="registration"
    )
    otp = serializers.RegexField(r"^\d{4}$")
    password = serializers.CharField(min_length=6, max_length=128, write_only=True)
    referral_code = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_referral_code(self, value):
        normalized = value.strip().upper()
        if normalized and not ReferralCode.objects.filter(code=normalized, is_active=True).exists():
            raise serializers.ValidationError("Invalid referral code")
        return normalized


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class MeSerializer(serializers.ModelSerializer):
    tenant_memberships = serializers.SerializerMethodField()
    active_context = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "tenant_memberships",
            "active_context",
        )

    def _memberships(self, obj):
        return obj.tenant_memberships.select_related("tenant", "role").prefetch_related(
            "accessible_branches__branch"
        ).filter(status="ACTIVE", tenant__status="ACTIVE")

    @staticmethod
    def _branches(membership):
        queryset = membership.tenant.branches.filter(status="ACTIVE")
        if membership.role.code != "OWNER":
            queryset = queryset.filter(membership_access__membership=membership)
        return [
            {"id": str(branch.id), "name": branch.name, "code": branch.code}
            for branch in queryset.order_by("name")
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_tenant_memberships(self, obj):
        return [
            {
                "id": str(membership.id),
                "tenant": {
                    "id": str(membership.tenant_id),
                    "name": membership.tenant.name,
                    "slug": membership.tenant.slug,
                },
                "role": {
                    "id": str(membership.role_id),
                    "code": membership.role.code,
                    "name": membership.role.name,
                },
                "accessible_branches": self._branches(membership),
            }
            for membership in self._memberships(obj)
        ]

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_active_context(self, obj):
        membership = resolve_tenant_context(self.context["request"], required=False)
        if membership is None:
            return None
        return {
            "tenant_id": str(membership.tenant_id),
            "membership_id": str(membership.id),
            "role": membership.role.code,
            "accessible_branches": self._branches(membership),
        }

