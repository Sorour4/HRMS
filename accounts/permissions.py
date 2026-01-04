from rest_framework.permissions import DjangoModelPermissions, BasePermission


class DjangoModelPermissionsWithView(DjangoModelPermissions):

    perms_map = DjangoModelPermissions.perms_map.copy()
    perms_map.update({
        "GET":    ["%(app_label)s.view_%(model_name)s"],
        "HEAD":   ["%(app_label)s.view_%(model_name)s"],
    })
    

class IsAdminGroup(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and u.is_authenticated and (u.is_superuser or u.groups.filter(name="Admin").exists())
        )