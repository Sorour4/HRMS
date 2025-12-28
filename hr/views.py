from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, RetrieveUpdateAPIView
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from accounts.models import User
from accounts.permissions import IsAdmin, IsAdminOrManager
from .models import Department, Employee, Attendance, Payroll
from .serializers import DepartmentSerializer, EmployeeSerializer, AttendanceSerializer, PayrollSerializer
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError, PermissionDenied


# TODO: re-implement the views using the other class based view (GenericAPIView, APIView)


def _get_user_department_id(request) -> int | None:
    user = (
        User.objects
        .select_related("employee")
        .only("id", "role", "employee__department_id")
        .get(id=request.user.id)
    )
    if hasattr(user, "employee") and user.employee and user.employee.department_id:
        return user.employee.department_id
    return None


def _get_user_with_employee(request) -> User:
    return (
        User.objects
        .select_related("employee")
        .only("id", "role", "employee__id", "employee__department_id")
        .get(id=request.user.id)
    )

class DepartmentListCreateView(ListCreateAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]

    # base queryset for serializer usage
    queryset = Department.objects.select_related("manager", "manager__user").order_by("id")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.role == User.Role.ADMIN:
            return qs

        dept_id = _get_user_department_id(self.request)
        if dept_id:
            return qs.filter(id=dept_id)

        return qs.none()

    def create(self, request, *args, **kwargs):
        # Admin-only create
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            raise PermissionDenied("You do not have permission to perform this action.")
        return super().create(request, *args, **kwargs)


class DepartmentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    queryset = Department.objects.select_related("manager", "manager__user").order_by("id")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.role == User.Role.ADMIN:
            return qs

        dept_id = _get_user_department_id(self.request)
        if dept_id:
            return qs.filter(id=dept_id)

        return qs.none()

    def update(self, request, *args, **kwargs):
        # Admin-only update/partial_update
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            raise PermissionDenied("You do not have permission to perform this action.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Admin-only destroy
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            raise PermissionDenied("You do not have permission to perform this action.")

        instance = self.get_object()
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "Cannot delete department because it has employees."})
        return super().destroy(request, *args, **kwargs)


class EmployeeListCreateView(ListCreateAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    queryset = Employee.objects.select_related("user", "department", "manager", "manager__user").order_by("id")

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

    def create(self, request, *args, **kwargs):
        # Only Admin can create
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            raise PermissionDenied("Only admins can create employees.")
        return super().create(request, *args, **kwargs)


class EmployeeDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    queryset = Employee.objects.select_related("user", "department", "manager", "manager__user").order_by("id")

    def get_queryset(self):
        # Same scoping rules as list so out-of-scope access becomes 404
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

    def update(self, request, *args, **kwargs):
        # Managers can update (but only within scoped queryset), Admin can update
        if request.user.role not in (User.Role.ADMIN, User.Role.MANAGER) and not request.user.is_superuser:
            raise PermissionDenied("You do not have permission to update employees.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Only Admin can delete
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            raise PermissionDenied("Only admins can delete employees.")
        return super().destroy(request, *args, **kwargs)
    
class AttendanceScopedMixin:
    """
    Shared queryset scoping logic to keep behavior identical to your ViewSet.
    """
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

    def _require_admin_or_manager(self, request):
        role = getattr(request.user, "role", None)
        if request.user.is_superuser:
            return
        if role in (User.Role.ADMIN, User.Role.MANAGER, "ADMIN", "MANAGER"):
            return
        raise ValidationError({"detail": "Employees cannot create attendance."})


class AttendanceListCreateView(AttendanceScopedMixin, ListCreateAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        self._require_admin_or_manager(request)
        return super().create(request, *args, **kwargs)


class AttendanceDetailUpdateView(AttendanceScopedMixin, RetrieveUpdateAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        self._require_admin_or_manager(request)
        return super().update(request, *args, **kwargs)


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

    def _require_admin(self, request):
        role = getattr(request.user, "role", None)
        if request.user.is_superuser or role in (User.Role.ADMIN, "ADMIN"):
            return
        raise ValidationError({"detail": "Not allowed."})


class PayrollListCreateView(PayrollScopedMixin, ListCreateAPIView):
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().create(request, *args, **kwargs)


class PayrollDetailView(PayrollScopedMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._require_admin(request)
        return super().destroy(request, *args, **kwargs)