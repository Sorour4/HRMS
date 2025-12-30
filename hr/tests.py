from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from hr.models import Department, Employee, Attendance, Payroll
from .status import PayrollStatus, AttendanceStatus


# ----------------------------
# Pagination helper (unchanged)
# ----------------------------

class PaginationMixin:
    """
    Works with paginated and non-paginated responses.
    After you enabled pagination, res.data is a dict with 'results'.
    """
    def results(self, res):
        return res.data["results"] if isinstance(res.data, dict) and "results" in res.data else res.data


# ------------------------------------
# Django groups/permissions test helpers
# ------------------------------------

def ensure_group(name: str) -> Group:
    group, _ = Group.objects.get_or_create(name=name)
    return group


def add_model_perms(group: Group, app_label: str, model: str, actions: list[str]):
    """
    actions: ["add", "change", "delete", "view"]
    """
    ct = ContentType.objects.get(app_label=app_label, model=model)
    codenames = [f"{a}_{model}" for a in actions]
    perms = Permission.objects.filter(content_type=ct, codename__in=codenames)
    group.permissions.add(*perms)


def setup_hr_test_groups():
    """
    Creates groups and assigns perms that match what your tests expect.
    Returns: (admin_group, manager_group, employee_group)
    """
    admin_g = ensure_group("Admin")
    manager_g = ensure_group("Manager")
    employee_g = ensure_group("Employee")

    # ADMIN: full control on all HR models
    for m in ["department", "employee", "attendance", "payroll"]:
        add_model_perms(admin_g, "hr", m, ["add", "change", "delete", "view"])

    # MANAGER:
    # - cannot create departments
    # - can view + change employees (within scoped queryset)
    # - can view/add/change attendance (within scoped queryset)
    # - can view payroll (read-only, within scoped queryset)
    # - can view department (for GET own dept)
    add_model_perms(manager_g, "hr", "employee", ["view", "change"])
    add_model_perms(manager_g, "hr", "attendance", ["view", "add", "change"])
    add_model_perms(manager_g, "hr", "payroll", ["view"])
    add_model_perms(manager_g, "hr", "department", ["view"])

    # EMPLOYEE:
    # view-only, scoping will limit to self/own dept
    add_model_perms(employee_g, "hr", "employee", ["view"])
    add_model_perms(employee_g, "hr", "attendance", ["view"])
    add_model_perms(employee_g, "hr", "payroll", ["view"])
    add_model_perms(employee_g, "hr", "department", ["view"])

    return admin_g, manager_g, employee_g


class HRPermsTestMixin:
    """
    Convenience mixin to assign groups in setUp without repeating logic.
    """
    @classmethod
    def setUpTestData(cls):
        # Ensure groups/perms exist once for the whole TestCase class.
        cls._admin_g, cls._manager_g, cls._employee_g = setup_hr_test_groups()

    def assign_groups(self, admin=None, manager=None, employees=None):
        if admin is not None:
            admin.groups.add(self._admin_g)
        if manager is not None:
            manager.groups.add(self._manager_g)
        if employees:
            for u in employees:
                u.groups.add(self._employee_g)


# -----------------
# Employee RBAC Tests
# -----------------

class EmployeeRBACAPITests(HRPermsTestMixin, PaginationMixin, APITestCase):
    def setUp(self):
        # Users
        self.admin = User.objects.create_user(
            username="admin1", password="Pass12345!", role=User.Role.ADMIN, email="admin1@test.com"
        )
        self.manager_user = User.objects.create_user(
            username="manager1", password="Pass12345!", role=User.Role.MANAGER, email="manager1@test.com"
        )
        self.employee_user = User.objects.create_user(
            username="employee1", password="Pass12345!", role=User.Role.EMPLOYEE, email="employee1@test.com"
        )
        self.other_employee_user = User.objects.create_user(
            username="employee2", password="Pass12345!", role=User.Role.EMPLOYEE, email="employee2@test.com"
        )

        # Assign groups/perms (NEW)
        self.assign_groups(
            admin=self.admin,
            manager=self.manager_user,
            employees=[self.employee_user, self.other_employee_user],
        )

        # Departments
        self.dept_a = Department.objects.create(name="Dept A", location="Floor 1")
        self.dept_b = Department.objects.create(name="Dept B", location="Floor 2")

        # Employee profiles
        self.manager_emp = Employee.objects.create(user=self.manager_user, department=self.dept_a)
        self.emp1 = Employee.objects.create(user=self.employee_user, department=self.dept_a, phone="111")
        self.emp2 = Employee.objects.create(user=self.other_employee_user, department=self.dept_b, phone="222")

        self.employees_url = "/api/employees/"

    def auth_as(self, user: User):
        self.client.force_authenticate(user=user)

    def test_employee_list_admin_sees_all(self):
        self.auth_as(self.admin)
        res = self.client.get(self.employees_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(self.results(res)), 3)

    def test_employee_list_manager_sees_only_department(self):
        self.auth_as(self.manager_user)
        res = self.client.get(self.employees_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        items = self.results(res)
        ids = {item["id"] for item in items}

        self.assertIn(self.manager_emp.id, ids)
        self.assertIn(self.emp1.id, ids)
        self.assertNotIn(self.emp2.id, ids)

    def test_employee_list_employee_sees_self_only(self):
        self.auth_as(self.employee_user)
        res = self.client.get(self.employees_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        items = self.results(res)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["user"], self.employee_user.id)

    def test_manager_can_update_employee_in_same_department(self):
        self.auth_as(self.manager_user)
        url = f"/api/employees/{self.emp1.id}/"
        res = self.client.patch(url, {"phone": "999"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.emp1.refresh_from_db()
        self.assertEqual(self.emp1.phone, "999")

    def test_manager_cannot_update_employee_in_other_department(self):
        self.auth_as(self.manager_user)
        url = f"/api/employees/{self.emp2.id}/"
        res = self.client.patch(url, {"phone": "888"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_employee_cannot_update_other_employee(self):
        self.auth_as(self.employee_user)
        url = f"/api/employees/{self.emp2.id}/"
        res = self.client.patch(url, {"phone": "777"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


# -----------------
# Department API Tests
# -----------------

class DepartmentAPITests(HRPermsTestMixin, PaginationMixin, APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1", password="Pass12345!", role=User.Role.ADMIN, email="admin1@test.com"
        )
        self.manager_user = User.objects.create_user(
            username="manager1", password="Pass12345!", role=User.Role.MANAGER, email="manager1@test.com"
        )
        self.employee_user = User.objects.create_user(
            username="employee1", password="Pass12345!", role=User.Role.EMPLOYEE, email="employee1@test.com"
        )

        # Assign groups/perms (NEW)
        self.assign_groups(
            admin=self.admin,
            manager=self.manager_user,
            employees=[self.employee_user],
        )

        self.dept_a = Department.objects.create(name="Dept A", location="Floor 1")
        self.dept_b = Department.objects.create(name="Dept B", location="Floor 2")

        self.manager_emp = Employee.objects.create(user=self.manager_user, department=self.dept_a)
        self.employee_emp = Employee.objects.create(user=self.employee_user, department=self.dept_a)

        self.departments_url = "/api/departments/"

    def auth_as(self, user):
        self.client.force_authenticate(user=user)

    def test_admin_can_create_department(self):
        self.auth_as(self.admin)
        res = self.client.post(self.departments_url, {"name": "Dept C", "location": "Floor 3"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_manager_cannot_create_department(self):
        self.auth_as(self.manager_user)
        res = self.client.post(self.departments_url, {"name": "Dept C"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_create_department(self):
        self.auth_as(self.employee_user)
        res = self.client.post(self.departments_url, {"name": "Dept C"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_sees_all_departments(self):
        self.auth_as(self.admin)
        res = self.client.get(self.departments_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(self.results(res)), 2)

    def test_manager_sees_only_own_department(self):
        self.auth_as(self.manager_user)
        res = self.client.get(self.departments_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        items = self.results(res)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], self.dept_a.id)

    def test_employee_sees_only_own_department(self):
        self.auth_as(self.employee_user)
        res = self.client.get(self.departments_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        items = self.results(res)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], self.dept_a.id)

    def test_admin_can_assign_department_manager_if_manager_role_and_same_department(self):
        self.auth_as(self.admin)
        url = f"/api/departments/{self.dept_a.id}/"
        res = self.client.patch(url, {"manager": self.manager_emp.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.dept_a.refresh_from_db()
        self.assertEqual(self.dept_a.manager_id, self.manager_emp.id)

    def test_admin_cannot_assign_manager_on_create(self):
        self.auth_as(self.admin)
        res = self.client.post(
            self.departments_url,
            {"name": "Dept X", "manager": self.manager_emp.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_cannot_assign_manager_from_other_department(self):
        self.auth_as(self.admin)
        url = f"/api/departments/{self.dept_b.id}/"
        res = self.client.patch(url, {"manager": self.manager_emp.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_cannot_delete_department_with_employees(self):
        self.auth_as(self.admin)
        url = f"/api/departments/{self.dept_a.id}/"
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# -----------------
# Attendance API Tests
# -----------------

class AttendanceAPITests(HRPermsTestMixin, PaginationMixin, APITestCase):
    def setUp(self):
        self.dept_a = Department.objects.create(name="Dept A", location="Loc A")
        self.dept_b = Department.objects.create(name="Dept B", location="Loc B")

        self.admin = User.objects.create_user(
            username="admin", password="pass1234", role=User.Role.ADMIN, email="admin_att@test.com"
        )
        self.manager_user = User.objects.create_user(
            username="mgr", password="pass1234", role=User.Role.MANAGER, email="mgr_att@test.com"
        )
        self.employee_user = User.objects.create_user(
            username="emp", password="pass1234", role=User.Role.EMPLOYEE, email="emp_att@test.com"
        )
        self.other_employee_user = User.objects.create_user(
            username="emp2", password="pass1234", role=User.Role.EMPLOYEE, email="emp2_att@test.com"
        )

        # Assign groups/perms (NEW)
        self.assign_groups(
            admin=self.admin,
            manager=self.manager_user,
            employees=[self.employee_user, self.other_employee_user],
        )

        self.manager_emp = Employee.objects.create(
            user=self.manager_user, department=self.dept_a, phone="1", salary=1000, join_date="2025-01-01"
        )
        self.emp_a = Employee.objects.create(
            user=self.employee_user, department=self.dept_a, phone="2", salary=900, join_date="2025-01-01"
        )
        self.emp_b = Employee.objects.create(
            user=self.other_employee_user, department=self.dept_b, phone="3", salary=900, join_date="2025-01-01"
        )

        self.a1 = Attendance.objects.create(employee=self.emp_a, date=date(2025, 12, 1), status="PRESENT")
        self.b1 = Attendance.objects.create(employee=self.emp_b, date=date(2025, 12, 1), status="ABSENT")

        self.list_url = reverse("attendance-list")

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_admin_sees_all_attendance(self):
        self.auth(self.admin)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(self.results(res)), 2)

    def test_manager_sees_only_department_attendance(self):
        self.auth(self.manager_user)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        items = self.results(res)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["employee"], self.emp_a.id)

    def test_employee_sees_only_own_attendance(self):
        self.auth(self.employee_user)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        items = self.results(res)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["employee"], self.emp_a.id)

    def test_employee_cannot_create_attendance(self):
        self.auth(self.employee_user)
        payload = {"employee": self.emp_a.id, "date": "2025-12-02", "status": "PRESENT"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_attendance_for_own_department(self):
        self.auth(self.manager_user)
        payload = {"employee": self.emp_a.id, "date": "2025-12-02", "status": "LATE"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_manager_cannot_create_attendance_outside_department(self):
        self.auth(self.manager_user)
        payload = {"employee": self.emp_b.id, "date": "2025-12-02", "status": "PRESENT"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_attendance_same_employee_same_date_rejected(self):
        self.auth(self.admin)
        payload = {"employee": self.emp_a.id, "date": "2025-12-01", "status": "ABSENT"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", res.data)

    def test_employee_cannot_access_other_employee_attendance_detail(self):
        self.auth(self.employee_user)
        detail_url = reverse("attendance-detail", args=[self.b1.id])
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


# -----------------
# Payroll API Tests
# -----------------

class PayrollAPITests(HRPermsTestMixin, PaginationMixin, APITestCase):
    def setUp(self):
        self.dept_a = Department.objects.create(name="Dept A", location="Floor 1")
        self.dept_b = Department.objects.create(name="Dept B", location="Floor 2")

        self.admin = User.objects.create_user(
            username="admin_pay", password="Pass12345!", role=User.Role.ADMIN, email="admin_pay@test.com"
        )
        self.manager_user = User.objects.create_user(
            username="mgr_pay", password="Pass12345!", role=User.Role.MANAGER, email="mgr_pay@test.com"
        )
        self.employee_user = User.objects.create_user(
            username="emp_pay", password="Pass12345!", role=User.Role.EMPLOYEE, email="emp_pay@test.com"
        )
        self.other_employee_user = User.objects.create_user(
            username="emp2_pay", password="Pass12345!", role=User.Role.EMPLOYEE, email="emp2_pay@test.com"
        )

        # Assign groups/perms (NEW)
        self.assign_groups(
            admin=self.admin,
            manager=self.manager_user,
            employees=[self.employee_user, self.other_employee_user],
        )

        self.manager_emp = Employee.objects.create(user=self.manager_user, department=self.dept_a, salary=Decimal("10000"))
        self.emp_a = Employee.objects.create(user=self.employee_user, department=self.dept_a, salary=Decimal("8000"))
        self.emp_b = Employee.objects.create(user=self.other_employee_user, department=self.dept_b, salary=Decimal("9000"))

        self.p1 = Payroll.objects.create(
            employee=self.emp_a,
            year=2025,
            month=12,
            base_salary=self.emp_a.salary,
            allowances=Decimal("200"),
            deductions=Decimal("50"),
            net_salary=Decimal("8150"),
            status=PayrollStatus.DRAFT,
        )
        self.p2 = Payroll.objects.create(
            employee=self.emp_b,
            year=2025,
            month=12,
            base_salary=self.emp_b.salary,
            allowances=Decimal("0"),
            deductions=Decimal("0"),
            net_salary=self.emp_b.salary,
            status=PayrollStatus.DRAFT,
        )

        self.list_url = reverse("payroll-list")

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_admin_list_sees_all(self):
        self.auth(self.admin)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(self.results(res)), 2)

    def test_manager_list_sees_only_department(self):
        self.auth(self.manager_user)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self.results(res)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["employee"], self.emp_a.id)

    def test_employee_list_sees_self_only(self):
        self.auth(self.employee_user)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self.results(res)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["employee"], self.emp_a.id)

    def test_admin_can_create_payroll_base_salary_forced_from_employee_salary(self):
        self.auth(self.admin)
        payload = {
            "employee": self.emp_a.id,
            "year": 2026,
            "month": 1,
            "allowances": "100.00",
            "deductions": "20.00",
            "status": "DRAFT",
        }
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # base_salary must match Employee.salary, net_salary computed
        self.assertEqual(Decimal(res.data["base_salary"]), self.emp_a.salary)
        self.assertEqual(Decimal(res.data["net_salary"]), self.emp_a.salary + Decimal("100.00") - Decimal("20.00"))

    def test_employee_cannot_create_payroll(self):
        self.auth(self.employee_user)
        payload = {"employee": self.emp_a.id, "year": 2026, "month": 1}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_cannot_create_payroll(self):
        self.auth(self.manager_user)
        payload = {"employee": self.emp_a.id, "year": 2026, "month": 1}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_payroll_same_employee_same_period_rejected(self):
        self.auth(self.admin)
        payload = {"employee": self.emp_a.id, "year": 2025, "month": 12}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", res.data)

    def test_employee_cannot_access_other_employee_payroll_detail(self):
        self.auth(self.employee_user)
        detail_url = reverse("payroll-detail", args=[self.p2.id])
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
