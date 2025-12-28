from django.urls import path
from hr.views import (
    DepartmentListCreateView,
    DepartmentDetailView,
    EmployeeListCreateView,
    EmployeeDetailView,
    AttendanceListCreateView,
    AttendanceDetailUpdateView,
    PayrollListCreateView,
    PayrollDetailView,
)

urlpatterns = [
    path("departments/", DepartmentListCreateView.as_view(), name="department-list"),
    path("departments/<int:pk>/", DepartmentDetailView.as_view(), name="department-detail"),
    path("employees/", EmployeeListCreateView.as_view(), name="employee-list"),
    path("employees/<int:pk>/", EmployeeDetailView.as_view(), name="employee-detail"),
    path("attendance/", AttendanceListCreateView.as_view(), name="attendance-list"),
    path("attendance/<int:pk>/", AttendanceDetailUpdateView.as_view(), name="attendance-detail"),
    path("payrolls/", PayrollListCreateView.as_view(), name="payroll-list"),
    path("payrolls/<int:pk>/", PayrollDetailView.as_view(), name="payroll-detail"),
]