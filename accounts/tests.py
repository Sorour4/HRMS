from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import User
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class AuthRBACTests(APITestCase):
    def setUp(self):
        # Users
        self.admin = User.objects.create_user(
            username="admin1",
            password="Pass12345!",
            role=User.Role.ADMIN,
            email="admin1@test.com",
        )
        self.manager = User.objects.create_user(
            username="manager1",
            password="Pass12345!",
            role=User.Role.MANAGER,
            email="manager1@test.com",
        )
        self.employee = User.objects.create_user(
            username="employee1",
            password="Pass12345!",
            role=User.Role.EMPLOYEE,
            email="employee1@test.com",
        )

        # Groups
        admin_g, _ = Group.objects.get_or_create(name="Admin")
        manager_g, _ = Group.objects.get_or_create(name="Manager")
        employee_g, _ = Group.objects.get_or_create(name="Employee")

        # HARD reset group permissions (prevents any automatic setup from leaking perms)
        admin_g.permissions.clear()
        manager_g.permissions.clear()
        employee_g.permissions.clear()

        # Give ONLY admin permission required for GET /users/ under DjangoModelPermissions
        app_label = User._meta.app_label
        model_name = User._meta.model_name
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        view_user = Permission.objects.get(content_type=ct, codename=f"view_{model_name}")
        admin_g.permissions.add(view_user)

        # Assign groups to users
        self.admin.groups.set([admin_g])
        self.manager.groups.set([manager_g])
        self.employee.groups.set([employee_g])

        # URLs
        self.login_url = "/api/auth/login/"
        self.refresh_url = "/api/auth/refresh/"
        self.me_url = "/api/auth/me/"
        self.users_url = "/api/users/"

    def login(self, username, password):
        return self.client.post(self.login_url, {"username": username, "password": password}, format="json")

    def auth_as(self, username, password):
        res = self.login(username, password)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        access = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return res.data

    def test_login_returns_tokens_and_user(self):
        res = self.login("manager1", "Pass12345!")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertIn("user", res.data)
        self.assertEqual(res.data["user"]["role"], User.Role.MANAGER)

    def test_me_requires_auth(self):
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        self.auth_as("employee1", "Pass12345!")
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], "employee1")
        self.assertEqual(res.data["role"], User.Role.EMPLOYEE)

    def test_refresh_returns_new_access(self):
        login_res = self.login("employee1", "Pass12345!")
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        refresh = login_res.data["refresh"]

        res = self.client.post(self.refresh_url, {"refresh": refresh}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)

    def test_admin_can_list_users(self):
        self.auth_as("admin1", "Pass12345!")
        res = self.client.get(self.users_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 3)

    def test_manager_cannot_list_users(self):
        self.auth_as("manager1", "Pass12345!")
        res = self.client.get(self.users_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_list_users(self):
        self.auth_as("employee1", "Pass12345!")
        res = self.client.get(self.users_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
