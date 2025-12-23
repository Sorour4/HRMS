from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import User


class AuthRBACTests(APITestCase):
    def setUp(self):
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

        self.login_url = "/api/auth/login/"
        self.refresh_url = "/api/auth/refresh/"
        self.me_url = "/api/auth/me/"
        self.users_url = "/api/users/"

    def login(self, username, password):
        res = self.client.post(self.login_url, {"username": username, "password": password}, format="json")
        return res

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
        # should return at least these 3 users
        self.assertGreaterEqual(len(res.data), 3)

    def test_manager_cannot_list_users(self):
        self.auth_as("manager1", "Pass12345!")
        res = self.client.get(self.users_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_list_users(self):
        self.auth_as("employee1", "Pass12345!")
        res = self.client.get(self.users_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)