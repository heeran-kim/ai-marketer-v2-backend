from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from businesses.models import Business
from .models import Promotion
from .serializers import PromotionSerializer

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def show(request):
    business = Business.objects.filter(owner=request.user).first()

    if not business:
        return Response({"error": "Business not found"}, status=404)

    promotions = Promotion.objects.filter(business=business).order_by("-created_at")
    serialized_promotions = PromotionSerializer(promotions, many=True).data

    response_data = {
        "promotions": serialized_promotions,
    }

    return Response(response_data)
