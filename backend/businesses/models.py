# backend/businesses/models.py
from django.db import models
from users.models import User

class Business(models.Model):
    """
    Business model representing a business entity owned by a user.
    Field lengths are standardized to 32 characters to match frontend constraints.
    """
    name = models.CharField(max_length=32)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    category = models.CharField(max_length=32, blank=True, null=True)  # Store the category of business
    target_customers = models.CharField(max_length=32, blank=True, null=True)  # Store target customer
    vibe = models.CharField(max_length=32, blank=True, null=True)  # Store vibe or theme of the business
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="businesses")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or "Unnamed Business"