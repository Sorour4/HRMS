from django.conf import settings
from django.db import models
from rest_framework.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

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
        # this will create N+1 query, handle the query to avoid this.
        return f"employee"
    

class Attendance(models.Model):
    class Status(models.TextChoices):
        # TODO: it's better to move these kind of classes to a different place/file
        # for better extendability and code cleanliness and easier reusability.

        #Can you show example of what can be done with these status?

        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "Late"
        LEAVE = "LEAVE", "Leave"

    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT)
    note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "date"], name="uniq_attendance_employee_date")
        ]
        indexes=[
            models.Index(fields=["date"])
        ]

    def clean(self):
        if self.date is None:
            raise ValidationError({"date": "Date is required."})

    def __str__(self):
        return f"{self.employee_id} - {self.date} - {self.status}"


class Payroll(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINAL = "FINAL", "Final"
        PAID = "PAID", "Paid"

    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.PROTECT,
        related_name="payrolls",
    )

    year = models.PositiveIntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])

    base_salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "year", "month"], name="uniq_payroll_employee_period")
        ]
        indexes=[
            models.Index(fields=["status"])
        ]

    def __str__(self):
        return f"{self.employee_id} {self.year}-{self.month:02d}"
    