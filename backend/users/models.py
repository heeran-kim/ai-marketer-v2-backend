from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import UserManager
from config.constants import ROLE_CHOICES, DEFAULT_ROLE

class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model using email as the unique identifier."""

    email = models.EmailField(unique=True, db_index=True) # Primary unique identifier for login, Index for faster lookups
    name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20,
        choices=[(role["key"], role["label"]) for role in ROLE_CHOICES],
        default=DEFAULT_ROLE
    )
    is_active = models.BooleanField(default=True) # Determines if the user can log in
    is_staff = models.BooleanField(default=False) # Needed for Django Admin panel access
    date_joined = models.DateTimeField(auto_now_add=True) # Stores when the user registered
    requires_2fa = models.BooleanField(default=False) # Boolean for if the user is using 2FA
    secret_2fa = models.CharField(max_length=255,blank=True,null=True) #The field for storing the TOTP

    access_token = models.CharField(max_length=512,blank=True, null=True) # Store the access token for Meta

    objects = UserManager() # Assign custom UserManager for object creation

    USERNAME_FIELD = "email" # Use email as the unique login field
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email # String representation of the user
    
    def save(self, *args, **kwargs):
        """Ensure email is always saved in lowercase."""
        self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    def is_admin(self):
        """Returns True if the user is an admin."""
        return self.role == "admin"

    def get_short_name(self):
        return self.name