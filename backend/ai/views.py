from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def analyse_image(request):
    """Upload image, save it, and return detected items."""
    if "image" not in request.FILES:
        return Response({"error": "No image uploaded"}, status=400)

    # TODO: CALL AI MODEL TO ANALYSE IMAGE
    MOCK_DETECTED_ITEMS = ["Steak", "Grilled Meat", "Garlic", "Herbs", "Lemon", "Lamb"]


    return Response({
        "detected_items": MOCK_DETECTED_ITEMS
    })
