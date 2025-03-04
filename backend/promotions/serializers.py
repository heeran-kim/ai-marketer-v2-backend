from rest_framework import serializers
from .models import Promotion
from posts.serializers import PostSerializer
from config.constants import PROMOTION_CATEGORIES_OPTIONS

class PromotionSerializer(serializers.ModelSerializer):
    posts = PostSerializer(many=True, read_only=True)
    categories = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id",
            "posts",
            "categories",
            "description",
            "start_date",
            "end_date",
            "status",
            "sold_count",
        ]

    def get_categories(self, obj):
        category_labels = {c["key"]: c["label"] for c in PROMOTION_CATEGORIES_OPTIONS}
        return [category_labels.get(category.key, category.key) for category in obj.categories.all()]