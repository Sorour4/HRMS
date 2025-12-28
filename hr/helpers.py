from accounts.models import User

def _get_user_department_id(request) -> int | None:
    user = (
        User.objects
        .select_related("employee")
        .only("id", "role", "employee__department_id")
        .get(id=request.user.id)
    )
    if hasattr(user, "employee") and user.employee and user.employee.department_id:
        return user.employee.department_id
    return None


def _get_user_with_employee(request) -> User:
    return (
        User.objects
        .select_related("employee")
        .only("id", "role", "employee__id", "employee__department_id")
        .get(id=request.user.id)
    )