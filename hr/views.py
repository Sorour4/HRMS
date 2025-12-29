from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from accounts.models import User
from accounts.permissions import IsAdmin, IsAdminOrManager
from .models import Department, Employee, Attendance, Payroll
from .serializers import (
    DepartmentSerializer,
    EmployeeSerializer,
    AttendanceSerializer,
    PayrollSerializer,
)
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError
from .helpers import _get_user_department_id, _get_user_with_employee


class DepartmentListCreateView(ListCreateAPIView):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.select_related("manager", "manager__user").order_by("id")

    def get_permissions(self):
        # Admin-only create, everyone authenticated can read (scoped)
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.role == User.Role.ADMIN:
            return qs

        dept_id = _get_user_department_id(self.request)
        if dept_id:
            return qs.filter(id=dept_id)

        return qs.none()


class DepartmentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.select_related("manager", "manager__user").order_by("id")

    def get_permissions(self):
        # Admin-only update/delete, everyone authenticated can read (scoped)
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.role == User.Role.ADMIN:
            return qs

        dept_id = _get_user_department_id(self.request)
        if dept_id:
            return qs.filter(id=dept_id)

        return qs.none()

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "Cannot delete department because it has employees."})


class EmployeeListCreateView(ListCreateAPIView):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.select_related("user", "department", "manager", "manager__user").order_by("id")

    def get_permissions(self):
        # Admin-only create, everyone authenticated can read (scoped)
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # Admin sees all
        if user.role == User.Role.ADMIN:
            return qs

        # Manager sees only department employees
        if user.role == User.Role.MANAGER:
            u = _get_user_with_employee(self.request)
            if not hasattr(u, "employee") or not u.employee or u.employee.department_id is None:
                return qs.none()
            return qs.filter(department_id=u.employee.department_id)

        # Employee sees only self
        return qs.filter(user=user)


class EmployeeDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.select_related("user", "department", "manager", "manager__user").order_by("id")

    def get_permissions(self):
        # Admin or Manager can update; Admin-only delete; everyone authenticated can read (scoped)
        if self.request.method in ("PUT", "PATCH"):
            return [IsAdminOrManager()]
        if self.request.method == "DELETE":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # Admin sees all
        if user.role == User.Role.ADMIN:
            return qs

        # Manager sees only department employees
        if user.role == User.Role.MANAGER:
            u = _get_user_with_employee(self.request)
            if not hasattr(u, "employee") or not u.employee or u.employee.department_id is None:
                return qs.none()
            return qs.filter(department_id=u.employee.department_id)

        # Employee sees only self
        return qs.filter(user=user)


class AttendanceScopedMixin:
    
    queryset = Attendance.objects.select_related("employee", "employee__user", "employee__department")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        role = getattr(user, "role", None)

        # Admin sees all
        if user.is_superuser or role == User.Role.ADMIN or role == "ADMIN":
            return qs

        # Manager sees department only
        if role == User.Role.MANAGER or role == "MANAGER":
            if not hasattr(user, "employee") or not user.employee.department_id:
                return qs.none()
            return qs.filter(employee__department_id=user.employee.department_id)

        # Employee sees self only
        if hasattr(user, "employee") and user.employee:
            return qs.filter(employee_id=user.employee.id)

        return qs.none()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class AttendanceListCreateView(AttendanceScopedMixin, ListCreateAPIView):
    serializer_class = AttendanceSerializer

    def get_permissions(self):
        # Admin/Manager can create, everyone authenticated can read (scoped)
        if self.request.method == "POST":
            return [IsAdminOrManager()]
        return [IsAuthenticated()]


class AttendanceDetailUpdateView(AttendanceScopedMixin, RetrieveUpdateAPIView):
    serializer_class = AttendanceSerializer

    def get_permissions(self):
        # Admin/Manager can update, everyone authenticated can read (scoped)
        if self.request.method in ("PUT", "PATCH"):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]


class PayrollScopedMixin:
    queryset = Payroll.objects.select_related("employee", "employee__user", "employee__department")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        role = getattr(user, "role", None)

        # Admin sees all
        if user.is_superuser or role in (User.Role.ADMIN, "ADMIN"):
            return qs

        # Manager sees only their department (read-only)
        if role in (User.Role.MANAGER, "MANAGER"):
            if not hasattr(user, "employee") or not user.employee.department_id:
                return qs.none()
            return qs.filter(employee__department_id=user.employee.department_id)

        # Employee sees only their own
        if hasattr(user, "employee") and user.employee:
            return qs.filter(employee_id=user.employee.id)

        return qs.none()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class PayrollListCreateView(PayrollScopedMixin, ListCreateAPIView):
    serializer_class = PayrollSerializer

    def get_permissions(self):
        # Admin-only create, everyone authenticated can read (scoped)
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]


class PayrollDetailView(PayrollScopedMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = PayrollSerializer

    def get_permissions(self):
        # Admin-only update/delete, everyone authenticated can read (scoped)
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return [IsAuthenticated()]