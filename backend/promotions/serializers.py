# promotions/serializers.py
from rest_framework import serializers
from .models import Promotion, PromotionSuggestion, PromotionCategories
from posts.serializers import PostSerializer
from django.utils import timezone

class PromotionSerializer(serializers.ModelSerializer):
    posts = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=PromotionCategories.objects.all(),
        many=True,
        write_only=True,
        source="categories"
    )
    categories = serializers.SerializerMethodField(read_only=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = Promotion
        fields = [
            "id",
            "posts",
            "category_ids",
            "categories",
            "description",
            "start_date",
            "end_date",
            "status",
            "sold_count",
        ]

    def get_categories(self, obj):
        return [
            {"id": category.id, "key": category.key, "label": category.label} 
            for category in obj.categories.all()
        ]
    
    def get_posts(self, obj):
        posts = obj.posts.all()
        return PostSerializer(posts, many=True, context=self.context).data
    
    # Calculate status dynamically based on current time vs. promotion dates
    def get_status(self, obj):
        now = timezone.now().date()
        if not obj.start_date and not obj.end_date:
            return "ongoing"
        
        if obj.start_date and not obj.end_date:
            return "ongoing" if now >= obj.start_date else "upcoming"
        
        if obj.start_date and obj.end_date:
            if now < obj.start_date:
                return "upcoming"
            elif obj.start_date <= now <= obj.end_date:
                return "ongoing"
            else:
                return "ended"
        
        return "unknown"
    
class SuggestionSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()

    class Meta:
        model = PromotionSuggestion
        fields = [
            "id",
            "title",
            "categories",
            "description",
        ]

    def get_categories(self, obj):
        return [
            {"id": category.id, "key": category.key, "label": category.label} 
            for category in obj.categories.all()
        ]
    