from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=200, unique=True)
    location = models.CharField(max_length=200, blank=True, null=True)

    # Manager is an Employee (not a User). Allow null until assigned.
    manager = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_departments",
    )

    def __str__(self):
        return self.name


class Employee(models.Model):
    # Link employee record to login account
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,  # prevent deleting dept with employees
        related_name="employees",
        null=True,
        blank=True,
    )

    # Self-relation for manager hierarchy
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates",
    )

    phone = models.CharField(max_length=30, blank=True, null=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    join_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}"