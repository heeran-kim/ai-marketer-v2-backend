# posts/serializers.py
from rest_framework import serializers
from .models import Post
from config.constants import SOCIAL_PLATFORMS

class PostSerializer(serializers.ModelSerializer):
    platform = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = "__all__"

    def get_platform(self, obj):
        if obj.platform:
            return dict(SOCIAL_PLATFORMS).get(obj.platform.platform, obj.platform.platform)
        return None

    def get_categories(self, obj):
        return [cat.label for cat in obj.categories.all()]