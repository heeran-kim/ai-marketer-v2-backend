import json
import logging

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from businesses.models import Business
from utils.openai_api import generate_captions

logger = logging.getLogger(__name__)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, JSONParser])
def generate_caption(request):
    """
    Generate AI-powered captions
    """
    data = request.data.copy()

    categories = json.loads(data.get("categories", []))
    business_info = json.loads(data.get("business_info", {}))
    item_info = json.loads(data.get("item_info", []))
    
    additional_prompt = data.get("additional_prompt", "")

    try:
        business = Business.objects.get(owner=request.user)
        business_info["name"] = business.name
        business_info["type"] = business.category
    except Business.DoesNotExist:
        return Response({"error": "Business not found"}, status=404)

    try:
        captions = generate_captions(
            categories=categories,
            business_info=business_info,
            item_info=item_info,
            additional_prompt=additional_prompt,
        )
        return Response({"captions": captions}, status=200)
    except Exception as e:
        logger.error(f"Error generating captions: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=500)


