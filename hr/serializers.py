from rest_framework import serializers
from accounts.models import User
from .models import Department, Employee, Attendance
from django.db import IntegrityError, transaction


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
    

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["id", "employee", "date", "status", "note", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        RBAC + data rules:
        - One attendance per employee per day (DB constraint; also validated here).
        - Manager can only create/update for employees in their department.
        - Employee cannot create/update (view-only for self).
        """
        request = self.context["request"]
        user = request.user

        # Only validate scope if employee provided (create) or existing instance (update)
        target_employee = attrs.get("employee") or getattr(self.instance, "employee", None)

        if not target_employee:
            return attrs

        # Admin can do anything
        if getattr(user, "role", None) == "ADMIN" or user.is_superuser:
            return attrs

        # Manager scope: must have employee profile and same department as target
        if getattr(user, "role", None) == "MANAGER":
            if not hasattr(user, "employee"):
                raise serializers.ValidationError("Manager must have an Employee profile.")

            if user.employee.department_id != target_employee.department_id:
                raise serializers.ValidationError("Managers can only manage attendance within their department.")
            return attrs

        # Employee role: no create/update
        raise serializers.ValidationError("Employees are not allowed to create or modify attendance records.")

    def create(self, validated_data):
        # Convert DB constraint error into clean 400
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({"date": "Attendance already exists for this employee on this date."})