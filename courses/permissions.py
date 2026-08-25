from rest_framework import permissions
from .helpers import is_instructor, is_admin


class IsInstructorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_instructor(request.user) or is_admin(request.user)


class IsAdminOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_admin(request.user)


class CanManageCourse(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if is_admin(request.user):
            return True
        return obj.instructor == request.user


class CanManageBook(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if is_admin(request.user):
            return True
        return obj.author == request.user
