from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
# Create your models here.


# TODO: it's a very good ides creating the custom manager, however, it's not used anywhere
# re-visit this part to determine do you really need to cstomize the manager or not and check 
# how you can use it, there is no point of customizing anything and not use it.
class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)  # force ADMIN role

        return super().create_superuser(username, email=email, password=password, **extra_fields)



class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        EMPLOYEE = "EMPLOYEE", "Employee"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    email = models.EmailField(unique=True, null=True, blank=True)