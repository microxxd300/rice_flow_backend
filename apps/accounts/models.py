from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone        = models.CharField(max_length=20, blank=True)
    barangay     = models.CharField(max_length=100, blank=True)
    municipality = models.CharField(max_length=100, default='Panabo City')
    province     = models.CharField(max_length=100, default='Davao del Norte')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"


class PasswordResetCode(models.Model):
    """A forgot-password code. Only its hash is kept; see password_reset.py for the rules."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_codes')
    code_hash  = models.CharField(max_length=64)
    attempts   = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    used_at    = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
