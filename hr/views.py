from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError

from .models import Department, Employee, Attendance, Payroll
from .serializers import (
    DepartmentSerializer,
    EmployeeSerializer,
    AttendanceSerializer,
    PayrollSerializer,
)
from .helpers import _get_user_department_id, _get_user_with_employee, has_global_scope, is_manager


# ---------
# Department
# ---------

class DepartmentListCreateView(ListCreateAPIView):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.select_related("manager", "manager__user").order_by("id")
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if has_global_scope(user):
            return qs

        dept_id = _get_user_department_id(self.request)
        if dept_id:
            return qs.filter(id=dept_id)

        return qs.none()


class DepartmentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.select_related("manager", "manager__user").order_by("id")
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if has_global_scope(user):
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


# ------
# Employee
# ------

class EmployeeListCreateView(ListCreateAPIView):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.select_related("user", "department", "manager", "manager__user").order_by("id")
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if has_global_scope(user):
            return qs

        if is_manager(user):
            u = _get_user_with_employee(self.request)
            if not hasattr(u, "employee") or not u.employee or u.employee.department_id is None:
                return qs.none()
            return qs.filter(department_id=u.employee.department_id) #not N+1 because of select_related

        return qs.filter(user=user)


class EmployeeDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.select_related("user", "department", "manager", "manager__user").order_by("id")
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if has_global_scope(user):
            return qs

        if is_manager(user):
            u = _get_user_with_employee(self.request)
            if not hasattr(u, "employee") or not u.employee or u.employee.department_id is None:
                return qs.none()
            return qs.filter(department_id=u.employee.department_id)

        return qs.filter(user=user)


# ----------
# Attendance
# ----------

class AttendanceScopedMixin:
    queryset = Attendance.objects.select_related("employee", "employee__user", "employee__department")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if has_global_scope(user):
            return qs

        if is_manager(user):
            if not hasattr(user, "employee") or not user.employee or not user.employee.department_id:
                return qs.none()
            return qs.filter(employee__department_id=user.employee.department_id) 

        if hasattr(user, "employee") and user.employee:
            return qs.filter(employee_id=user.employee.id)

        return qs.none()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class AttendanceListCreateView(AttendanceScopedMixin, ListCreateAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]


class AttendanceDetailUpdateView(AttendanceScopedMixin, RetrieveUpdateAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]


# -------
# Payroll
# -------

class PayrollScopedMixin:
    queryset = Payroll.objects.select_related("employee", "employee__user", "employee__department")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if has_global_scope(user):
            return qs

        if is_manager(user):
            if not hasattr(user, "employee") or not user.employee or not user.employee.department_id:
                return qs.none()
            return qs.filter(employee__department_id=user.employee.department_id)

        if hasattr(user, "employee") and user.employee:
            return qs.filter(employee_id=user.employee.id)

        return qs.none()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class PayrollListCreateView(PayrollScopedMixin, ListCreateAPIView):
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]


class PayrollDetailView(PayrollScopedMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]