# promotions/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from businesses.models import Business
from .models import Promotion, PromotionSuggestion
from .serializers import PromotionSerializer, SuggestionSerializer

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