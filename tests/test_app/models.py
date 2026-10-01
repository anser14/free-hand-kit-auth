from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Host-owned custom user model with an application-specific field."""

    department = models.CharField(max_length=80, blank=True)
