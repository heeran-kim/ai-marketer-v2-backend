# promotions/views.py
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from django.db.models import Sum, Min, Max
from pytz import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from businesses.models import Business
from sales.models import SalesDataPoint
from utils.openai_api import generate_promotions
from utils.square_api import get_square_menu_items

from .models import Promotion, PromotionCategories, PromotionSuggestion
from .serializers import PromotionSerializer, SuggestionSerializer

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
                return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Only return non-dismissed suggestions by default
            show_dismissed = self.request.query_params.get('show_dismissed', 'false').lower() == 'true'
            queryset = PromotionSuggestion.objects.filter(business=business)

            if not show_dismissed:
                queryset = queryset.filter(is_dismissed=False)
            
            return queryset.order_by("-created_at")
        else:
            if not business:
                return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
            
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
        
        # Get the suggestion ID from which the promotion is being created
        suggestion_id = request.data.get('suggestion_id')

        # If creating from a suggestion, get product names from it
        if suggestion_id:
            try:
                suggestion = PromotionSuggestion.objects.get(id=suggestion_id, business=business)
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save(business=business, product_names=suggestion.product_names, product_data=suggestion.product_data)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except PromotionSuggestion.DoesNotExist:
                pass

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
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss a suggestion with optional feedback"""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            suggestion = PromotionSuggestion.objects.get(pk=pk, business=business)
        except PromotionSuggestion.DoesNotExist:
            return Response({"error": "Suggestion not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Store the feedback
        feedback_text = request.data.get('feedback', '')
        suggestion.is_dismissed = True
        suggestion.feedback = feedback_text
        suggestion.save()

        return Response({"message": "Suggestion dismissed successfully"}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate promotion suggestions"""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Auto-archive old suggestions to ensure there's room for new ones
        self._auto_archive_suggestions(business)

        # Fetching performance and pricing data
        products_performance = self._get_products_performance(business)
        context_data = {
            "name": business.name,
            "type": business.category,
            "target_customers": business.target_customers,
            "vibe": business.vibe
        }
        feedback_context = self._get_feedback_context(business)

        ai_input_payload= {
            "products_performance": products_performance,
            "context_data": context_data,
            "feedback_history": feedback_context
        }

        try:
            # Generate promotions
            suggestions_data = generate_promotions(ai_input_payload)

            suggestion_instances = []
            for suggestion in suggestions_data:
                product_names = suggestion.get('product_name', [])
                products_with_categories = []
                for product_name in product_names:
                    product_info = next(
                        (p for p in products_performance['products'] if p['product_name'] == product_name), 
                        None
                    )
                    if product_info:
                        products_with_categories.append({
                            'name': product_name,
                            'category': product_info['category']
                        })
                    else:
                        products_with_categories.append({
                            'name': product_name,
                            'category': 'average'
                        })

                suggestion_instance = PromotionSuggestion(
                    business=business,
                    title=suggestion.get('title'),
                    description=suggestion.get('description'),
                    product_names=product_names,
                    product_data=products_with_categories,
                    data_start_date=products_performance.get('start_date'),
                    data_end_date=products_performance.get('end_date'),
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

    def _auto_archive_suggestions(self, business, days=30, max_active_count = 5):
        start_date = datetime.now(timezone('UTC')) - timedelta(days)
        old_suggestions = PromotionSuggestion.objects.filter(
            business=business,
            is_dismissed=False,
            created_at__lt=start_date
        )

        if old_suggestions.exists():
            old_suggestions.update(
                is_dismissed=True,
                feedback="Auto-archived due to age"
            )
        
        current_active_count = PromotionSuggestion.objects.filter(
            business=business,
            is_dismissed=False
        ).count()

        if current_active_count > max_active_count:
            to_keep = max_active_count
            to_archive = current_active_count - to_keep

            if to_archive > 0:
                oldest_ids = PromotionSuggestion.objects.filter(
                    business=business,
                    is_dismissed=False
                ).order_by('created_at').values_list('id', flat=True)[:to_archive]

                PromotionSuggestion.objects.filter(id__in=oldest_ids).update(
                    is_dismissed=True,
                    feedback="Auto-archived to make room for new suggestions"
                )


    def _get_products_performance(self, business, days=30):
        """
        Analyses sales data to classify products based on performance and recent sales trends.

        This function calculates total revenue and units sold for each product, ranks them, and classifies the top and bottom 10% as high-performing or low-performing respectively.
        It also evaluates recent sales trends (upward, downward, or flat) for each product using exponential moving average (EMA).
        """
        # Get Square data
        square_data = get_square_menu_items(business)

        # Calculate the date range
        start_date = datetime.now(timezone('UTC')) - timedelta(days)
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
    
    def _get_feedback_context(self, business):
        recent_dismissed = PromotionSuggestion.objects.filter(business=business, is_dismissed=True).exclude(feedback=None).exclude(feedback='').exclude(feedback__startswith="Auto-archived").order_by('-created_at')[:5]

        feedback_context = []
        if recent_dismissed.exists():
            for dismissed in recent_dismissed:
                if dismissed.product_names and dismissed.feedback:
                    feedback_context.append({
                        'product_names': dismissed.product_names,
                        'feedback': dismissed.feedback
                    })

        return feedback_context
    