from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from common.models import UUIDTimeStampedModel

from .managers import UserManager


class User(UUIDTimeStampedModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ("email",)

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class PasswordResetCode(UUIDTimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_codes")
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(blank=True, null=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Password reset for {self.user.email}"


class RegistrationCode(UUIDTimeStampedModel):
    pharmacy_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, db_index=True)
    email = models.EmailField(db_index=True)
    postal_code = models.CharField(max_length=20)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField(db_index=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)


class ReferralCode(UUIDTimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class BlockedPhoneNumber(UUIDTimeStampedModel):
    phone = models.CharField(max_length=30, unique=True)
    reason = models.CharField(max_length=255, blank=True)

