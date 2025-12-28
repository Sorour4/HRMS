from rest_framework.permissions import BasePermission
from accounts.models import User

# TODO: many of these permissions are not used, if it's not needed just remove it.
# PS:isn't it better to have them, even if they aren't used at this time ?

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN)


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.MANAGER)


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.EMPLOYEE)


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in [User.Role.ADMIN, User.Role.MANAGER]
        )


class IsSelfOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.role == User.Role.ADMIN:
            return True

        # obj is User
        if isinstance(obj, User):
            return obj.id == request.user.id

        # obj has user (Employee profile)
        if hasattr(obj, "user_id"):
            return obj.user_id == request.user.id

        # obj has employee.user (Attendance/Payroll)
        if hasattr(obj, "employee") and hasattr(obj.employee, "user_id"):
            return obj.employee.user_id == request.user.id

        return False