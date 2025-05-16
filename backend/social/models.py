from django.db import models

from businesses.models import Business
from config.constants import SOCIAL_PLATFORMS

class SocialMedia(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="social_media_links")
    platform = models.CharField(
        max_length=20,
        choices=[(platform["key"], platform["label"]) for platform in SOCIAL_PLATFORMS],
    )
    link = models.URLField()  # Store the social media link for this platform
    username = models.CharField(max_length=255)  # Store username

    class Meta:
        unique_together = ('business', 'platform')  # Ensure one account per platform per business

    def __str__(self):
        return f"{self.platform} - {self.business.name}"