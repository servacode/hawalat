"""حوالات — صلاحيات الأدوار المركزية (RBAC — ق4)."""

from rest_framework.permissions import BasePermission


def _has_role(request, role):
    user = request.user
    return bool(user and user.is_authenticated and user.role == role)


class IsPlatformAdmin(BasePermission):
    """الأدمن — إداري بحت، لا يصل لأي بيانات مالية."""

    def has_permission(self, request, view):
        return _has_role(request, "admin")


class IsBigOffice(BasePermission):
    def has_permission(self, request, view):
        return _has_role(request, "big_office")


class IsSmallOffice(BasePermission):
    def has_permission(self, request, view):
        return _has_role(request, "small_office")
