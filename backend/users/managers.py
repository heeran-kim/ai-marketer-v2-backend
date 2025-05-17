import logging

from django.contrib.auth.models import BaseUserManager

from config.constants import ROLE_CHOICES, DEFAULT_ROLE

logger = logging.getLogger(__name__)

class UserManager(BaseUserManager):
    """Custom manager for the User model, handling user and supersuer creation."""

    def create_user(self, email, name, password=None, role=DEFAULT_ROLE, **extra_fields):
        """Creates and returns a regular user with the given email and password."""
        if not email:
            raise ValueError("The Email field must be set")
        if not name:
            raise ValueError("The Name field must be set")
        if not password:
            raise ValueError("The Password field must be set")
        if role not in [choice["key"] for choice in ROLE_CHOICES]:
            raise ValueError(f"Invalid role. Choose one of: {[choice['key'] for choice in ROLE_CHOICES]}")

        email = self.normalize_email(email.strip()) # Remove spaces, normalize format
        user = self.model(email=email, name=name, role=role, **extra_fields)
        user.set_password(password) # Hash and store the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        """Creates and returns a superuser with full permissions."""
        extra_fields.setdefault("is_staff", True) # Required for Django Admin access
        extra_fields.setdefault("is_superuser", True) # Gives all permissions
        
        # Prevent accidental overrides (if someone tries to pass False)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, name, password, role="admin", **extra_fields)