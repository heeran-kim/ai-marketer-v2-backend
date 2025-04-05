# promotions/serializers.py
from rest_framework import serializers
from .models import Promotion, PromotionSuggestion
from posts.serializers import PostSerializer
from django.utils import timezone

class PromotionSerializer(serializers.ModelSerializer):
    posts = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

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
        return [
            {"id": category.id, "key": category.key, "label": category.label} 
            for category in obj.categories.all()
        ]
    
    # Calculate status dynamically based on current time vs. promotion dates
    def get_status(self, obj):
        now = timezone.now()
        if now < obj.start_date:
            return "upcoming"
        elif obj.start_date <= now <= obj.end_date:
            return "ongoing"
        else:
            return "ended"
        
    def get_posts(self, obj):
        posts = obj.posts.all()
        return PostSerializer(posts, many=True, context=self.context).data

    def validate(self, data):
        # Ensure end data is after start date
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError("End date must be after start date")
        return data 
    
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
        return [{"key": category.key, "label": category.label} for category in obj.categories.all()]

    def validate(self, data):
        # Ensure end data is after start date
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError("End date must be after start date")
        return data 
    
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