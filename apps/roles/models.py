from django.db import models

from common.models import UUIDTimeStampedModel


class Permission(UUIDTimeStampedModel):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return self.code


class Role(UUIDTimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

