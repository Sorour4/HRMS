from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def setup_hr_groups():
    HR_MODELS = ["department", "employee", "attendance", "payroll"]
    ACTIONS = ["add", "change", "delete", "view"]

    def get_perm(model, action):
        ct = ContentType.objects.get(app_label="hr", model=model)
        return Permission.objects.get(content_type=ct, codename=f"{action}_{model}")

    admin, _ = Group.objects.get_or_create(name="Admin")
    hr_staff, _ = Group.objects.get_or_create(name="HR Staff")
    manager, _ = Group.objects.get_or_create(name="Manager")
    employee, _ = Group.objects.get_or_create(name="Employee")

    # Admin: all perms on HR models
    admin.permissions.set([get_perm(m, a) for m in HR_MODELS for a in ACTIONS])

    # HR Staff: tweak as needed
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

    # Manager: usually department-scoped in queryset
    manager.permissions.set([
        get_perm("department", "view"),
        get_perm("employee", "view"),
        get_perm("attendance", "add"),
        get_perm("attendance", "change"),
        get_perm("attendance", "view"),
        get_perm("payroll", "view"),
    ])

    # Employee: self-scoped in queryset
    employee.permissions.set([
        get_perm("employee", "view"),
        get_perm("attendance", "view"),
        get_perm("payroll", "view"),
    ])