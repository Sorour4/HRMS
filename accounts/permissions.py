from rest_framework.permissions import DjangoModelPermissions


class DjangoModelPermissionsWithView(DjangoModelPermissions):

    perms_map = DjangoModelPermissions.perms_map.copy()
    perms_map.update({
        "GET":    ["%(app_label)s.view_%(model_name)s"],
        "HEAD":   ["%(app_label)s.view_%(model_name)s"],
    })


