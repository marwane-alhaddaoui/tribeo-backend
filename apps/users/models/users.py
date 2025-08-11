from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
import re
from apps.users.managers.user_manager import CustomUserManager

USERNAME_REGEX = re.compile(r"^[a-z0-9_]{3,20}$")

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('coach', 'Coach'),
        ('user', 'User'),
    ]

    email = models.EmailField(unique=True, max_length=255)
    username = models.CharField(max_length=20, unique=True, blank=False, null=False, db_index=True)  # 🆕
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def clean(self):
        super().clean()
        if self.username:
            self.username = self.username.lower()
            if not USERNAME_REGEX.match(self.username):
                raise ValidationError("Le nom d'utilisateur doit faire 3-20 caractères, avec lettres, chiffres ou underscore uniquement.")

    class Meta:
        constraints = [
            UniqueConstraint(Lower('username'), name='unique_username_ci')
        ]

    def __str__(self):
        return self.username or self.email
