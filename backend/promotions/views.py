# promotions/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from businesses.models import Business
from .models import Promotion, PromotionCategories, PromotionSuggestion
from .serializers import PromotionSerializer, SuggestionSerializer
from sales.models import SalesDataPoint
from utils.square_api import get_square_summary
from utils.openai_api import generate_promotions

from datetime import datetime, timedelta
from pytz import timezone
from decimal import Decimal
from django.db.models import Sum, Min, Max
import logging

logger = logging.getLogger(__name__)

class PromotionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        # Dynamically choose serializer based on query parameter
        type_param = self.request.query_params.get('type')
        
        if type_param == 'suggestions':
            return SuggestionSerializer
        
        # Default to PromotionSerializer
        return PromotionSerializer
    
    def get_queryset(self):
        type_param = self.request.query_params.get('type')
        business = Business.objects.filter(owner=self.request.user).first()

        if type_param == 'suggestions':
            if not business:
                return PromotionSuggestion.objects.none()
            
            return PromotionSuggestion.objects.filter(business=business).order_by("-created_at")
        else:
            if not business:
                return Promotion.objects.none()
            
            return Promotion.objects.filter(business=business).order_by("-created_at")
        
    def get_promotion(self, pk, user):
        business = Business.objects.filter(owner=user).first()
        if not business:
            return None, Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            promotion = Promotion.objects.get(pk=pk, business=business)
            return promotion, None
        except Promotion.DoesNotExist:
            return None, Response({"error": "Promotion not found"}, status=status.HTTP_404_NOT_FOUND)
        
    def list(self, request, *args, **kwargs):
        """Retrieve all promotions or suggestions"""
        response = super().list(request, *args, **kwargs)
        
        type_param = self.request.query_params.get('type')
        if type_param == 'suggestions':
            business = Business.objects.filter(owner=self.request.user).first()
            has_sales_data = False

            if business:
                has_sales_data = SalesDataPoint.objects.filter(business=business).exists()
            
            response.data = {
                "has_sales_data": has_sales_data,
                "suggestions": response.data
            }

        return response
        
    def retrieve(self, request, pk=None):
        """Retrieve a specific promotion"""
        promotion, error_response = self.get_promotion(pk, request.user)
        if error_response:
            return error_response

        serializer = self.get_serializer(promotion)
        return Response(serializer.data)
    
    def destroy(self, request, pk=None):
        """Delete a specific promotion"""
        promotion, error_response = self.get_promotion(pk, request.user)
        if error_response:
            return error_response
        
        promotion.delete()
        return Response({"message": "Promotion deleted successfully"}, status=status.HTTP_200_OK)
    
    def create(self, request):
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(business=business)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update a specific promotion"""
        partial = kwargs.pop('partial', False)
        promotion, error_response = self.get_promotion(kwargs.get('pk'), request.user)
        if error_response:
            return error_response
        
        serializer = self.get_serializer(promotion, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate promotion suggestions"""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)

        # Fetching performance and pricing data
        products_performance = self._get_products_performance(business)
        context_data = {
            "name": business.name,
            "type": business.category,
            "target_customers": business.target_customers,
            "vibe": business.vibe
        }

        ai_input_payload= {
            "products_performance": products_performance,
            "context_data": context_data
        }

        try:
            # Generate promotions
            suggestions_data = generate_promotions(ai_input_payload)

            suggestion_instances = []
            for suggestion in suggestions_data:
                suggestion_instance = PromotionSuggestion(
                    business=business,
                    title=suggestion['title'],
                    description=suggestion['description'],
                )
                suggestion_instances.append(suggestion_instance)

            # Bulk create the valid suggestions
            created_suggestions = PromotionSuggestion.objects.bulk_create(suggestion_instances)

            # Generate categories and associate them
            for suggestion, suggestion_instance in zip(suggestions_data, created_suggestions):
                # Ensure categories exist in the database
                categories = PromotionCategories.objects.filter(key__in=suggestion['category'])
                
                if categories.exists():
                    # Set categories if they exist
                    suggestion_instance.categories.set(categories)
                    suggestion_instance.save()  # Save the instance after setting categories
                else:
                    logger.error(f"Category '{suggestion['category']}' not found in the database.")

            return Response({"success": "Promotion suggestions generated successfully"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error generating promotion suggestions: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def _get_products_performance(self, business, days=30):
        """
        Analyses sales data to classify products based on performance and recent sales trends.

        This function calculates total revenue and units sold for each product, ranks them, and classifies the top and bottom 10% as high-performing or low-performing respectively.
        It also evaluates recent sales trends (upward, downward, or flat) for each product using exponential moving average (EMA).
        """
        # Get Square data
        square_data = get_square_summary(business)

        # Calculate the date range
        start_date = (datetime.now(timezone('UTC')) - timedelta(days))
        end_date = datetime.now(timezone('UTC'))

        # Filter the sales data based on the given date range
        sales_data = SalesDataPoint.objects.filter(business_id=business.id, date__range=[start_date, end_date])
        
        # Group the data by product_name and calculate total revenue and units sold
        grouped = sales_data.values('product_name') \
            .annotate(total_revenue=Sum('revenue'), total_units=Sum('units_sold'))
        
        total = len(grouped)
        top_10_percent = max(int(total * 0.1), 1)
        bottom_10_percent = max(int(total * 0.1), 1)
        
        # Sort products by total revenue in descending order
        sorted_products = sorted(grouped, key=lambda x: x['total_revenue'], reverse=True)

        product_names = [product['product_name'] for product in sorted_products]
        
        # Map product names to their respective sales data, filtered by date range
        product_data_map = {
            name: sales_data.filter(product_name=name).order_by('-date') 
            for name in product_names
        }

        # Calculate trends for each product using a helper function (_calculate_trend)
        product_trends = {
            name: self._calculate_trend(product_data_map[name])
            for name in product_data_map
        }

        # Assign performance category and trend to each product
        for i, product in enumerate(sorted_products):
            trend = product_trends[product['product_name']]

            if i < top_10_percent :
                product['category'] = 'top_10_percent'
            elif i >= total - bottom_10_percent:
                product['category'] = 'bottom_10_percent'
            else:
                product['category'] = 'average'
            
            # Add the trend for each product
            product['trend'] = trend

            # Add product description and price from square data
            if square_data['items'] and product['product_name'].lower() in square_data['items']:
                product['description_with_price'] = square_data['items'][product['product_name'].lower()]

        # Calculate the overall start_date and end_date for the analysis period
        overall_start_date = sales_data.aggregate(Min('date'))['date__min']
        overall_end_date = sales_data.aggregate(Max('date'))['date__max']

        result = {
            'start_date': overall_start_date,
            'end_date': overall_end_date,
            'products': sorted_products
        }
        
        return result

    def _calculate_trend(self, product_data, days=14, smoothing_factor=0.1, threshold=0.05):
        """
        Calculates the sales trend for a product based on its recent revenue data using Exponential Moving Average (EMA).

        The function retrieves the last `days` number of revenue data points for the product and computes an Exponential Moving Average (EMA) to assess the trend. EMA is used because it gives more weight to the most recent data, making it more responsive to changes in trends.

        Parameters:
        smoothing_factor (float): The weight given to the most recent data point. A value between 0 and 1. Default is 0.1.
        threshold (float): The maximum allowable difference between the latest revenue and the EMA to be considered as 'flat'. Default is 0.05 (5%).
        """
        
        smoothing_factor = Decimal(smoothing_factor)

        revenues = product_data.order_by('-date').values_list('revenue', flat=True)[:days]

        if len(revenues) < days:
            return 'flat'
        
        ema = revenues[0]
        
        for revenue in revenues[1:]:
            ema = (smoothing_factor * revenue) + ((1 - smoothing_factor) * ema)
        
        if abs(revenues[0] - ema) <= threshold:
            return 'flat'
        elif revenues[0] > ema:
            return 'upward'
        elif revenues[0] < ema:
            return 'downward'
        
        return 'flat'

    