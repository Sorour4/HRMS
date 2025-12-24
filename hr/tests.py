from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from accounts.models import User
from hr.models import Department, Employee, Attendance
from datetime import date


class EmployeeRBACAPITests(APITestCase):
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
        self.assertGreaterEqual(len(res.data), 3)

    def test_employee_list_manager_sees_only_department(self):
        self.auth_as(self.manager_user)
        res = self.client.get(self.employees_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in res.data}
        self.assertIn(self.manager_emp.id, ids)
        self.assertIn(self.emp1.id, ids)
        self.assertNotIn(self.emp2.id, ids)

    def test_employee_list_employee_sees_self_only(self):
        self.auth_as(self.employee_user)
        res = self.client.get(self.employees_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["user"], self.employee_user.id)

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
        # because queryset hides it, it should look like "not found"
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_employee_cannot_update_other_employee(self):
        self.auth_as(self.employee_user)
        url = f"/api/employees/{self.emp2.id}/"
        res = self.client.patch(url, {"phone": "777"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class DepartmentAPITests(APITestCase):
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
        self.assertGreaterEqual(len(res.data), 2)

    def test_manager_sees_only_own_department(self):
        self.auth_as(self.manager_user)
        res = self.client.get(self.departments_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], self.dept_a.id)

    def test_employee_sees_only_own_department(self):
        self.auth_as(self.employee_user)
        res = self.client.get(self.departments_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], self.dept_a.id)

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
        # manager_emp is in Dept A, try assign as manager of Dept B
        url = f"/api/departments/{self.dept_b.id}/"
        res = self.client.patch(url, {"manager": self.manager_emp.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_cannot_delete_department_with_employees(self):
        self.auth_as(self.admin)
        url = f"/api/departments/{self.dept_a.id}/"
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

class AttendanceAPITests(APITestCase):
    def setUp(self):
        # Departments
        self.dept_a = Department.objects.create(name="Dept A", location="Loc A")
        self.dept_b = Department.objects.create(name="Dept B", location="Loc B")

        # Users
        self.admin = User.objects.create_user(username="admin", password="pass1234", role="ADMIN",email="admin_att@test.com")
        self.manager_user = User.objects.create_user(username="mgr", password="pass1234", role="MANAGER",email="mgr_att@test.com")
        self.employee_user = User.objects.create_user(username="emp", password="pass1234", role="EMPLOYEE",email="emp_att@test.com")
        self.other_employee_user = User.objects.create_user(username="emp2", password="pass1234", role="EMPLOYEE",email="emp2_att@test.com")

        # Employee profiles
        self.manager_emp = Employee.objects.create(user=self.manager_user, department=self.dept_a, phone="1", salary=1000, join_date="2025-01-01")
        self.emp_a = Employee.objects.create(user=self.employee_user, department=self.dept_a, phone="2", salary=900, join_date="2025-01-01")
        self.emp_b = Employee.objects.create(user=self.other_employee_user, department=self.dept_b, phone="3", salary=900, join_date="2025-01-01")

        # Attendance records
        self.a1 = Attendance.objects.create(employee=self.emp_a, date=date(2025, 12, 1), status="PRESENT")
        self.b1 = Attendance.objects.create(employee=self.emp_b, date=date(2025, 12, 1), status="ABSENT")

        self.list_url = reverse("attendance-list")

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_admin_sees_all_attendance(self):
        self.auth(self.admin)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_manager_sees_only_department_attendance(self):
        self.auth(self.manager_user)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["employee"], self.emp_a.id)

    def test_employee_sees_only_own_attendance(self):
        self.auth(self.employee_user)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["employee"], self.emp_a.id)

    def test_employee_cannot_create_attendance(self):
        self.auth(self.employee_user)
        payload = {"employee": self.emp_a.id, "date": "2025-12-02", "status": "PRESENT"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

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
        # Should be 404 due to scoped queryset
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
