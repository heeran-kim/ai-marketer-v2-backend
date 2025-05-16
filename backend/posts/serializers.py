# posts/serializers.py
from rest_framework import serializers

from config.constants import SOCIAL_PLATFORMS

from .models import Post

class PostSerializer(serializers.ModelSerializer):
    platform = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField() 

    class Meta:
        model = Post
        fields = "__all__"

    def get_platform(self, obj):
        if obj.platform:
            return dict(SOCIAL_PLATFORMS).get(obj.platform.platform, obj.platform.platform)
        return None

    def get_categories(self, obj):
        return [cat.label for cat in obj.categories.all()]
    
    # Generates absolute URLs when request object is available
    def get_image(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url
