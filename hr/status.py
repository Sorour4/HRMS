from django.db import models


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"
    LATE = "LATE", "Late"
    LEAVE = "LEAVE", "Leave"

class PayrollStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    FINAL = "FINAL", "Final"
    PAID = "PAID", "Paid"