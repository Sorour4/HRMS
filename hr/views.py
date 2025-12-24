from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from accounts.models import User
from accounts.permissions import IsAdmin, IsAdminOrManager
from .models import Department, Employee
from .serializers import DepartmentSerializer, EmployeeSerializer
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError



class DepartmentViewSet(ModelViewSet):
    queryset = Department.objects.all().select_related("manager", "manager__user")
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        # Admin-only for write operations
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdmin()]
        # Any authenticated user can read (but queryset is filtered)
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.role == User.Role.ADMIN:
            return qs

        # Manager/Employee: only their own department
        if hasattr(user, "employee") and user.employee.department_id:
            return qs.filter(id=user.employee.department_id)

        return qs.none()

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "Cannot delete department because it has employees."})


class EmployeeViewSet(ModelViewSet):
    queryset = Employee.objects.all().select_related("user", "department", "manager", "manager__user")
    serializer_class = EmployeeSerializer

    def get_permissions(self):
        # Admin can do anything
        if self.request.user and self.request.user.is_authenticated and self.request.user.role == "ADMIN":
            return [IsAuthenticated()]

        # Managers can UPDATE employees
        if self.action in ["update", "partial_update"]:
            return [IsAdminOrManager()]

        # Only Admin can create/delete 
        if self.action in ["create", "destroy"]:
            return [IsAdmin()]

        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.role == User.Role.ADMIN:
            return qs

        # Manager must have employee profile + dept 
        if user.role == User.Role.MANAGER:
            if not hasattr(user, "employee") or user.employee.department_id is None:
                return qs.none()
            return qs.filter(department_id=user.employee.department_id)

        # Employee sees only self
        return qs.filter(user=user)
