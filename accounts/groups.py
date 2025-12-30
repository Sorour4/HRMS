# hr/groups.py (or accounts/groups.py if you prefer)
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def setup_hr_groups():
    HR_MODELS = ["department", "employee", "attendance", "payroll"]
    ACTIONS = ["add", "change", "delete", "view"]

    def get_perm(model, action):
        ct = ContentType.objects.get(app_label="hr", model=model)
        perm = Permission.objects.filter(content_type=ct, codename=f"{action}_{model}").first()
        if not perm:
            raise RuntimeError(f"Missing permission: hr.{action}_{model} (did you migrate?)")
        return perm

    admin, _ = Group.objects.get_or_create(name="Admin")
    hr_staff, _ = Group.objects.get_or_create(name="HR Staff")
    manager, _ = Group.objects.get_or_create(name="Manager")
    employee, _ = Group.objects.get_or_create(name="Employee")

    admin.permissions.set([get_perm(m, a) for m in HR_MODELS for a in ACTIONS])

    hr_staff.permissions.set([
        get_perm("department", "view"),
        get_perm("employee", "add"),
        get_perm("employee", "change"),
        get_perm("employee", "view"),
        get_perm("attendance", "add"),
        get_perm("attendance", "change"),
        get_perm("attendance", "view"),
        get_perm("payroll", "add"),
        get_perm("payroll", "change"),
        get_perm("payroll", "view"),
    ])

    manager.permissions.set([
        get_perm("department", "view"),
        get_perm("employee", "view"),
        get_perm("attendance", "add"),
        get_perm("attendance", "change"),
        get_perm("attendance", "view"),
        get_perm("payroll", "view"),
    ])

    employee.permissions.set([
        get_perm("employee", "view"),
        get_perm("attendance", "view"),
        get_perm("payroll", "view"),
    ])

    return {
        "Admin": admin.permissions.count(),
        "HR Staff": hr_staff.permissions.count(),
        "Manager": manager.permissions.count(),
        "Employee": employee.permissions.count(),
    }
