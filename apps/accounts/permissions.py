"""
Admin console roles, from the Django flags already on the user:

    is_superuser  -> admin      everything (the developers)
    is_staff      -> validator  the agriculturist engineer: reads the admin data
                                and corrects variety values, but cannot manage
                                accounts, delete records, import data, retrain
                                models or change the suitability rules.

Validator access uses DRF's IsAdminUser (is_staff); admin-only actions use IsSuperUser.
"""
from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """Allows access only to active superusers (the admin role)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_active and user.is_superuser)


def can_see_contacts(user):
    """Farmer emails and phone numbers are for admins only (Data Privacy Act)."""
    return bool(user and user.is_superuser)
