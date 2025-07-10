from enum import StrEnum, auto
from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin


class Role(StrEnum):
    ADMIN = auto()
    SUPPORT = auto()
    DRIVER = auto()
    CUSTOMER = auto()

    @classmethod
    def choices(cls):
        results = []

        for item in cls:
            _element: tuple[str, str] = (item.value, item.name.lower().capitalize())
            results.append(_element)
        
        return results


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str, **extra_fields):
        """Create and save a USER with passed parameters"""

        email = self.normalize_email(email)
        password = make_password(password)
        
        extra_fields["is_staff"] = False
        extra_fields["is_superuser"] = False
        extra_fields["role"] = Role.CUSTOMER
        
        # aka User(...)
        user = self.model(email=email, password=password, **extra_fields)
        user.save()

        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        """Create and save a SUPERUSER with passed parameters"""
        
        email = self.normalize_email(email)
        password = make_password(password)
        
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["role"] = Role.ADMIN
        
        # aka User(...)
        user = self.model(email=email, password=password, **extra_fields)
        user.save()

        return user

class User(AbstractBaseUser, PermissionsMixin):
    class Meta:
        db_table = "users"

    objects = UserManager()

    email = models.EmailField(max_length=100, unique=True, null=False)
    phone_number = models.CharField(max_length=13, unique=True, null=False)
    first_name = models.CharField(max_length=30, null=False)
    last_name = models.CharField(max_length=50, null=False)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    role = models.CharField(
        max_length=50, default=Role.CUSTOMER, choices=Role.choices()
    )

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    