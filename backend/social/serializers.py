from rest_framework import serializers

from config.constants import SOCIAL_PLATFORMS

from .models import SocialMedia

class SocialMediaSerializer(serializers.ModelSerializer):
    key = serializers.CharField(source="platform")
    label = serializers.SerializerMethodField()

    class Meta:
        model = SocialMedia
        fields = ["key", "label", "link", "username"]

    def get_label(self, obj):
        """Retrieve label from SOCIAL_PLATFORMS based on platform key"""
        return next((p["label"] for p in SOCIAL_PLATFORMS if p["key"] == obj.platform), obj.platform)