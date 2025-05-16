# backend/businesses/serializers.py
from rest_framework import serializers
from .models import Business

class BusinessSerializer(serializers.ModelSerializer):
    """Serializer for the Business model with field validation"""

    class Meta:
        model = Business
        fields = ['id', 'name', 'logo', 'category', 'target_customers', 'vibe']
        read_only_fields = ['id']

    def validate_name(self, value):
        """Validate that business name is at least 3 characters long."""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Business name must be at least 3 characters.")
        if len(value) > 32:
            raise serializers.ValidationError("Business name cannot exceed 32 characters.")
        return value

    def validate_category(self, value):
        """Validate category field length."""
        if value and len(value) > 32:
            raise serializers.ValidationError("Category cannot exceed 32 characters.")
        return value

    def validate_target_customers(self, value):
        """Validate target_customers field length."""
        if value and len(value) > 32:
            raise serializers.ValidationError("Target customers description cannot exceed 32 characters.")
        return value

    def validate_vibe(self, value):
        """Validate vibe field length."""
        if value and len(value) > 32:
            raise serializers.ValidationError("Vibe description cannot exceed 32 characters.")
        return value
    

class PlaceIDLookupSerializer(serializers.Serializer):
    place_id = serializers.CharField(required=True)
    
class BusinessDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ['id', 'name', 'category', 'logo_url', 'place_id', 'address', 'phone', 'website']