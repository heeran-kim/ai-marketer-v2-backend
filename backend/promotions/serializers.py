# promotions/serializers.py
from datetime import timedelta
import logging

from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from posts.serializers import PostSerializer
from sales.models import SalesDataPoint

from .models import Promotion, PromotionSuggestion, PromotionCategories

logger = logging.getLogger(__name__)

class PromotionSerializer(serializers.ModelSerializer):
    posts = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=PromotionCategories.objects.all(),
        many=True,
        write_only=True,
        source="categories"
    )
    categories = serializers.SerializerMethodField()
    end_date = serializers.DateField(required=False, allow_null=True)
    product_names = serializers.JSONField(required=False, allow_null=True)
    products = serializers.SerializerMethodField()
    sold_count = serializers.SerializerMethodField()
    sales_change = serializers.SerializerMethodField()

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
            "sales_change",
            "product_names",
            "products",
        ]

    def get_categories(self, obj):
        return [
            {"id": category.id, "key": category.key, "label": category.label} 
            for category in obj.categories.all()
        ]
    
    def get_posts(self, obj):
        posts = obj.posts.all()
        return PostSerializer(posts, many=True, context=self.context).data

    def get_products(self, obj):
        # Return products with categories if product_data is available
        if hasattr(obj, 'product_data') and obj.product_data:
            return obj.product_data
        
        # Otherwise, convert from product_names (backward compatibility)
        elif obj.product_names:
            return [{'name': name, 'category': 'average'} for name in obj.product_names]
        
        return []
    
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
    
    def get_sold_count(self, obj): 
        if self.get_status(obj) == "upcoming":
            return 0
        
        today = timezone.now().date()
        start_date = obj.start_date

        if obj.end_date and obj.end_date < today:
            end_date = obj.end_date
        else:
            end_date = today
        
        promotion_days = (end_date - start_date).days + 1

        if promotion_days < 1:
            return 0
        
        products = self.get_products(obj)
        if not products:
            return None
        product_names = [product['name'] for product in products]

        promotion_sales = SalesDataPoint.objects.filter(
            business=obj.business,
            product_name__in=product_names,
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total=Sum('units_sold'))['total'] or 0

        return promotion_sales

    def get_sales_change(self, obj):
        if self.get_status(obj) == "upcoming":
            return None
        
        today = timezone.now().date()
        start_date = obj.start_date

        if obj.end_date and obj.end_date < today:
            end_date = obj.end_date
        else:
            end_date = today
        
        promotion_days = (end_date - start_date).days + 1

        if promotion_days < 1:
            return None
        
        products = self.get_products(obj)
        if not products:
            return None
        product_names = [product['name'] for product in products]

        promotion_sales = self.get_sold_count(obj)

        days_to_look_back = 30
        before_start_date = start_date - timedelta(days=days_to_look_back)
        before_end_date = start_date - timedelta(days=1)

        total_back_days = (before_end_date - before_start_date).days + 1
        num_periods = total_back_days // promotion_days
        num_periods = max(1, num_periods)

        period_sales_list = []

        for i in range(num_periods):
            period_end = before_end_date - timedelta(days=i * promotion_days)
            period_start = max(before_start_date, period_end - timedelta(days=promotion_days - 1))
            
            if period_start > period_end:
                continue

            period_sales = SalesDataPoint.objects.filter(
                business=obj.business,
                product_name__in=product_names,
                date__gte=period_start,
                date__lte=period_end
            ).aggregate(total=Sum('units_sold'))['total'] or 0
            
            period_sales_list.append(period_sales)
        
        if not period_sales_list:
            return 0
            
        avg_period_sales = sum(period_sales_list) / len(period_sales_list)

        if avg_period_sales == 0:
            return promotion_sales
        
        return round(promotion_sales - avg_period_sales, 1)
    
class SuggestionSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()
    product_names = serializers.JSONField(required=False, allow_null=True)
    products = serializers.SerializerMethodField(read_only=True)
    data_period = serializers.SerializerMethodField()

    class Meta:
        model = PromotionSuggestion
        fields = [
            "id",
            "title",
            "categories",
            "description",
            "product_names",
            "products",
            "data_period",
            "is_dismissed",
        ]

    def get_categories(self, obj):
        return [
            {"id": category.id, "key": category.key, "label": category.label} 
            for category in obj.categories.all()
        ]
    
    def get_products(self, obj):
        # Return products with categories if product_data is available
        if hasattr(obj, 'product_data') and obj.product_data:
            return obj.product_data
        
        # Otherwise, convert from product_names (backward compatibility)
        elif obj.product_names:
            return [{'name': name, 'category': 'average'} for name in obj.product_names]
        
        return []
    
    def get_data_period(self, obj):
        """Format date range used for generating suggestion"""
        if not obj.data_start_date or not obj.data_end_date:
            return None
        
        return {
            "start_date": obj.data_start_date.isoformat(),
            "end_date": obj.data_end_date.isoformat()
        }
    