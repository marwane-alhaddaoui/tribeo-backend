# apps/users/managers/user_manager.py
from django.contrib.auth.models import BaseUserManager
import re

USERNAME_RX = re.compile(r"^[a-z0-9_]{3,20}$")

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _normalize_username(self, username: str) -> str:
        if not username:
            raise ValueError("username is required")
        u = username.strip().lower()
        if not USERNAME_RX.match(u):
            raise ValueError("Username must be 3–20 chars: a-z, 0-9, _ only.")
        return u

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("email is required")
        email = self.normalize_email(email)
        username = self._normalize_username(username)

        # Sécurité: personne ne choisit son rôle à l’inscription via le manager
        role = extra_fields.get("role", "user")
        extra_fields["role"] = "user" if role not in ("admin", "coach") else role

        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields["role"] = "admin"

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)
