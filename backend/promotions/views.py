# promotions/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from businesses.models import Business
from .models import Promotion
from .serializers import PromotionSerializer

class PromotionListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PromotionSerializer

    def get_queryset(self):
        business = Business.objects.filter(owner=self.request.user).first()
        if not business:
            return Promotion.objects.none()
        
        return Promotion.objects.filter(business=business).order_by("-created_at")
    
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serialized_promotions = self.get_serializer(queryset, many=True, context={'request': request}).data

        response_data = {
            "promotions": serialized_promotions,
        }

        return Response(response_data)

class PromotionDetialView(APIView):
    permission_classes = [IsAuthenticated]

    def get_promotion(self, pk, user):
        business = Business.objects.filter(owner=user).first()
        if not business:
            return None, Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            promotion = Promotion.objects.get(pk=pk, business=business)
            return promotion, None
        except Promotion.DoesNotExist:
            return None, Response({"error": "Promotion not found"}, status=status.HTTP_404_NOT_FOUND)
        
    def get(self, request, pk):
        """Retrieve a specific promotion"""
        promotion, error_response = self.get_promotion(pk, request.user)
        if error_response:
            return error_response

        serializer = PromotionSerializer(promotion, context={'request': request})
        return Response(serializer.data)
    
    def delete(self, request, pk):
        """Delete a promotion"""
        promotion, error_response = self.get_promotion(pk, request.user)
        if error_response:
            return error_response
        
        promotion.delete()
        return Response({"message": "Promotion deleted successfully"}, status=status.HTTP_200_OK)