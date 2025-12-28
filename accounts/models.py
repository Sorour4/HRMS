from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
# Create your models here.




class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        EMPLOYEE = "EMPLOYEE", "Employee"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    email = models.EmailField(unique=True, null=True, blank=True)