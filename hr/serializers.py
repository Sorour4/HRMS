from rest_framework import serializers
from accounts.models import User
from .models import Department, Employee


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "location", "manager"]

    def validate_manager(self, manager_employee):
        if manager_employee is None:
            return None

        # Block setting manager on CREATE
        if self.instance is None:
            raise serializers.ValidationError(
                "Set department manager after creating the department (use PATCH)."
            )

        # Must be MANAGER role
        if manager_employee.user.role != User.Role.MANAGER:
            raise serializers.ValidationError("Department manager must have role MANAGER.")

        # Must belong to the same department
        if manager_employee.department_id != self.instance.id:
            raise serializers.ValidationError("Manager must belong to the same department.")

        return manager_employee


class EmployeeSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    user_role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "user_username",
            "user_role",
            "department",
            "manager",
            "phone",
            "salary",
            "join_date",
        ]

    def validate(self, attrs):
        manager = attrs.get("manager", getattr(self.instance, "manager", None))

        # Prevent self manager (on update)
        if self.instance and manager and manager.id == self.instance.id:
            raise serializers.ValidationError({"manager": "Employee cannot be their own manager."})

        # If manager is assigned, require manager role = MANAGER (or ADMIN if you want)
        if manager and manager.user.role != User.Role.MANAGER:
            raise serializers.ValidationError({"manager": "Manager must have role MANAGER."})

        return attrs