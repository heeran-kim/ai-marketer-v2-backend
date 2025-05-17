# backend/businesses/models.py
from django.conf import settings
from django.db import models

from users.models import User

def business_logo_path(instance, filename):
    return f'business_logos/{instance.id}/logo.jpg'

class Business(models.Model):
    """
    Business model representing a business entity owned by a user.
    Field lengths are standardized to 32 characters to match frontend constraints.
    """
    name = models.CharField(max_length=32)
    if settings.TEMP_MEDIA_DISCORD_WEBHOOK:
        logo = models.CharField(max_length=255, blank=True, null=True)  # Store the url of the logo
    else:
        logo = models.ImageField(upload_to=business_logo_path, blank=True, null=True)
    category = models.CharField(max_length=32, blank=True, null=True)  # Store the category of business
    target_customers = models.CharField(max_length=32, blank=True, null=True)  # Store target customer
    vibe = models.CharField(max_length=32, blank=True, null=True)  # Store vibe or theme of the business
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="businesses")
    square_access_token = models.CharField(max_length=255, blank=True, null=True)  # Store Square access token
    last_square_sync_at = models.DateTimeField(null=True, blank=True)  # Store last sync time with Square
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or "Unnamed Business"