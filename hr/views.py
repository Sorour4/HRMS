from rest_framework.viewsets import ModelViewSet
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from accounts.models import User
from accounts.permissions import IsAdmin, IsAdminOrManager
from .models import Department, Employee, Attendance, Payroll
from .serializers import DepartmentSerializer, EmployeeSerializer, AttendanceSerializer, PayrollSerializer
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError


# TODO: re-implement the views using the other class based view (GenericAPIView, APIView)
class DepartmentViewSet(ModelViewSet):
    queryset = Department.objects.all().select_related("manager", "manager__user").order_by("id")
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

        # TODO: trying to access user.employe.department_id will introduce N+1 query
        # this needs to be handled.
        if hasattr(user, "employee") and user.employee.department_id:
            return qs.filter(id=user.employee.department_id)

        return qs.none()

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "Cannot delete department because it has employees."})


class EmployeeViewSet(ModelViewSet):
    queryset = Employee.objects.all().select_related("user", "department", "manager", "manager__user").order_by("id")
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
    
class AttendanceViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - GET /api/attendance/            (paginated)
    - GET /api/attendance/<id>/
    - POST /api/attendance/           (Admin or Manager only)
    - PATCH /api/attendance/<id>/     (Admin or Manager only)
    """
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]
    queryset = Attendance.objects.select_related("employee", "employee__user", "employee__department")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        role = getattr(user, "role", None)
        if role == "ADMIN" or user.is_superuser:
            return qs

        if role == "MANAGER":
            # If manager missing employee profile -> return nothing (consistent with your 404 style)
            if not hasattr(user, "employee") or not user.employee.department_id:
                return qs.none()
            return qs.filter(employee__department_id=user.employee.department_id)

        # EMPLOYEE: only self
        if hasattr(user, "employee"):
            return qs.filter(employee_id=user.employee.id)

        return qs.none()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class PayrollViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated]
    queryset = Payroll.objects.select_related("employee", "employee__user", "employee__department")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        role = getattr(user, "role", None)

        # Admin sees all
        if user.is_superuser or role == "ADMIN":
            return qs

        # Manager sees payroll for employees in their department (read-only by serializer)
        if role == "MANAGER":
            if not hasattr(user, "employee") or not user.employee.department_id:
                return qs.none()
            return qs.filter(employee__department_id=user.employee.department_id)

        # Employee sees only their own
        if hasattr(user, "employee"):
            return qs.filter(employee_id=user.employee.id)

        return qs.none()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx