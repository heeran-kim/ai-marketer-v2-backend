# backend/sales/serializers.py
from rest_framework import serializers
from .models import SalesData

class SalesDataSerializer(serializers.ModelSerializer):
    """Serializer for the SalesData model"""
    class Meta:
        model = SalesData
        fields = ['id', 'filename', 'file_type', 'uploaded_at', 'processed', 'processed_at']
