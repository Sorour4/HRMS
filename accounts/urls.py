from django.urls import path
from .views import(
    MeView,
    UserListView,
    CustomTokenObtainPairView,
    GroupListCreateView,
    DefaultHRGroupsView,
    PermissionListView,
    GroupAddPermissionsView,
    GroupRemovePermissionsView,)
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

urlpatterns = [
    path("auth/me/", MeView.as_view(), name="me"),
    path("users/", UserListView.as_view(), name="list-users"),
     path("auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("admin/groups/", GroupListCreateView.as_view(), name="admin-group-list-create"),
    path("admin/seed-hr-groups/", DefaultHRGroupsView.as_view(), name="admin-seed-hr-groups"),
    path("admin/permissions/", PermissionListView.as_view(), name="admin-permission-list"),
    path("admin/groups/<int:pk>/add-permissions/", GroupAddPermissionsView.as_view(), name="admin-group-add-perms"),
    path("admin/groups/<int:pk>/remove-permissions/", GroupRemovePermissionsView.as_view(), name="admin-group-remove-perms"),
]