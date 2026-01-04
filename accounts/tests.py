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


class AdminGroupPermissionsAPITests(APITestCase):
    def results(self, res):
        return res.data["results"] if isinstance(res.data, dict) and "results" in res.data else res.data

    def setUp(self):

        self.admin = User.objects.create_user(
            username="admin1", password="Pass12345!", role=User.Role.ADMIN, email="admin1@test.com"
        )
        self.manager = User.objects.create_user(
            username="manager1", password="Pass12345!", role=User.Role.MANAGER, email="manager1@test.com"
        )
        self.employee = User.objects.create_user(
            username="employee1", password="Pass12345!", role=User.Role.EMPLOYEE, email="employee1@test.com"
        )


        self.admin_group, _ = Group.objects.get_or_create(name="Admin")
        self.manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.employee_group, _ = Group.objects.get_or_create(name="Employee")

        self.admin_group.permissions.clear()
        self.manager_group.permissions.clear()
        self.employee_group.permissions.clear()

        self.admin.groups.set([self.admin_group])
        self.manager.groups.set([self.manager_group])
        self.employee.groups.set([self.employee_group])

        self.login_url = "/api/auth/login/"
        self.permissions_url = "/api/admin/permissions/"

        self.target_group = Group.objects.create(name="HR Auditors")

        self.add_perms_url = f"/api/admin/groups/{self.target_group.id}/add-permissions/"
        self.remove_perms_url = f"/api/admin/groups/{self.target_group.id}/remove-permissions/"

        ct = ContentType.objects.get(app_label=User._meta.app_label, model=User._meta.model_name)
        self.view_user_perm = Permission.objects.get(content_type=ct, codename=f"view_{User._meta.model_name}")

    def auth_as(self, username, password):
        res = self.client.post(self.login_url, {"username": username, "password": password}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        access = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_admin_can_list_permissions(self):
        self.auth_as("admin1", "Pass12345!")
        res = self.client.get(self.permissions_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        items = self.results(res)

        # Defensive: ensure we're iterating over dict items, not strings
        ids = {item["id"] for item in items if isinstance(item, dict) and "id" in item}
        self.assertIn(self.view_user_perm.id, ids)

    def test_manager_cannot_list_permissions(self):
        self.auth_as("manager1", "Pass12345!")
        res = self.client.get(self.permissions_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_list_permissions(self):
        self.auth_as("employee1", "Pass12345!")
        res = self.client.get(self.permissions_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_add_permissions_to_group(self):
        self.auth_as("admin1", "Pass12345!")

        payload = {"permission_ids": [self.view_user_perm.id]}
        res = self.client.post(self.add_perms_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.target_group.refresh_from_db()
        self.assertTrue(self.target_group.permissions.filter(id=self.view_user_perm.id).exists())

    def test_manager_cannot_add_permissions_to_group(self):
        self.auth_as("manager1", "Pass12345!")

        payload = {"permission_ids": [self.view_user_perm.id]}
        res = self.client.post(self.add_perms_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_add_permissions_to_group(self):
        self.auth_as("employee1", "Pass12345!")

        payload = {"permission_ids": [self.view_user_perm.id]}
        res = self.client.post(self.add_perms_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_permission_id_returns_400(self):
        self.auth_as("admin1", "Pass12345!")

        payload = {"permission_ids": [99999999]}  # invalid
        res = self.client.post(self.add_perms_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_remove_permissions_from_group(self):
        # First add a perm to the target group directly
        self.target_group.permissions.add(self.view_user_perm)

        self.auth_as("admin1", "Pass12345!")
        payload = {"permission_ids": [self.view_user_perm.id]}
        res = self.client.post(self.remove_perms_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.target_group.refresh_from_db()
        self.assertFalse(self.target_group.permissions.filter(id=self.view_user_perm.id).exists())


    def test_manager_cannot_remove_permissions_from_group(self):
        self.target_group.permissions.add(self.view_user_perm)

        self.auth_as("manager1", "Pass12345!")
        payload = {"permission_ids": [self.view_user_perm.id]}
        res = self.client.post(self.remove_perms_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


    def test_employee_cannot_remove_permissions_from_group(self):
        self.target_group.permissions.add(self.view_user_perm)

        self.auth_as("employee1", "Pass12345!")
        payload = {"permission_ids": [self.view_user_perm.id]}
        res = self.client.post(self.remove_perms_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


    def test_remove_permissions_invalid_permission_id_returns_400(self):
        self.auth_as("admin1", "Pass12345!")
        payload = {"permission_ids": [99999999]}
        res = self.client.post(self.remove_perms_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class AdminUserGroupAssignmentTests(APITestCase):
    def setUp(self):

        self.admin = User.objects.create_user(
            username="admin1", password="Pass12345!", role=User.Role.ADMIN, email="admin1@test.com"
        )
        self.manager = User.objects.create_user(
            username="manager1", password="Pass12345!", role=User.Role.MANAGER, email="manager1@test.com"
        )
        self.employee = User.objects.create_user(
            username="employee1", password="Pass12345!", role=User.Role.EMPLOYEE, email="employee1@test.com"
        )


        self.admin_group, _ = Group.objects.get_or_create(name="Admin")
        self.manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.hr_staff_group, _ = Group.objects.get_or_create(name="HR Staff")


        self.admin_group.permissions.clear()
        self.manager_group.permissions.clear()
        self.hr_staff_group.permissions.clear()


        self.admin.groups.set([self.admin_group])
        self.manager.groups.set([self.manager_group])

        self.login_url = "/api/auth/login/"


        self.target_user = self.employee

        self.add_groups_url = f"/api/admin/users/{self.target_user.id}/add-groups/"
        self.remove_groups_url = f"/api/admin/users/{self.target_user.id}/remove-groups/"

    def auth_as(self, username, password):
        res = self.client.post(self.login_url, {"username": username, "password": password}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        access = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_admin_can_add_groups_to_user(self):
        self.auth_as("admin1", "Pass12345!")

        payload = {"group_ids": [self.hr_staff_group.id]}
        res = self.client.post(self.add_groups_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.groups.filter(id=self.hr_staff_group.id).exists())

    def test_admin_can_remove_groups_from_user(self):
        # Pre-assign group
        self.target_user.groups.add(self.hr_staff_group)

        self.auth_as("admin1", "Pass12345!")
        payload = {"group_ids": [self.hr_staff_group.id]}
        res = self.client.post(self.remove_groups_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.groups.filter(id=self.hr_staff_group.id).exists())

    def test_manager_cannot_add_groups_to_user(self):
        self.auth_as("manager1", "Pass12345!")
        payload = {"group_ids": [self.hr_staff_group.id]}
        res = self.client.post(self.add_groups_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_group_id_returns_400(self):
        self.auth_as("admin1", "Pass12345!")
        payload = {"group_ids": [99999999]}
        res = self.client.post(self.add_groups_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class AdminUserDetailWithAuthTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1", password="Pass12345!", role=User.Role.ADMIN, email="admin1@test.com"
        )
        self.employee = User.objects.create_user(
            username="employee1", password="Pass12345!", role=User.Role.EMPLOYEE, email="employee1@test.com"
        )

        self.admin_group, _ = Group.objects.get_or_create(name="Admin")
        self.hr_staff_group, _ = Group.objects.get_or_create(name="HR Staff")

        self.admin_group.permissions.clear()
        self.hr_staff_group.permissions.clear()

        self.admin.groups.set([self.admin_group])

        self.employee.groups.set([self.hr_staff_group])

        ct = ContentType.objects.get(app_label=User._meta.app_label, model=User._meta.model_name)
        view_user = Permission.objects.get(content_type=ct, codename=f"view_{User._meta.model_name}")
        self.hr_staff_group.permissions.add(view_user)

        self.login_url = "/api/auth/login/"
        self.detail_url = f"/api/admin/users/{self.employee.id}/detail/"

    def auth_as(self, username, password):
        res = self.client.post(self.login_url, {"username": username, "password": password}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        access = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_admin_can_view_user_detail_with_groups_and_permissions(self):
        self.auth_as("admin1", "Pass12345!")
        res = self.client.get(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["username"], "employee1")
        self.assertIn("groups", res.data)
        self.assertIn("permissions", res.data)

        self.assertIn("HR Staff", res.data["groups"])

        expected_perm = f"{User._meta.app_label}.view_{User._meta.model_name}"
        self.assertIn(expected_perm, res.data["permissions"])

    def test_non_admin_cannot_view_user_detail(self):
        self.auth_as("employee1", "Pass12345!")
        res = self.client.get(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)