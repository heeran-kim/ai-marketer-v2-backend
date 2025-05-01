from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from utils.openai_api import generate_captions
from utils.discord_api import upload_image_file_to_discord, delete_discord_message
from businesses.models import Business
import json
import logging
import time

logger = logging.getLogger(__name__)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def analyse_image(request):
    """
    Analyse an uploaded image and return detected items (Mock Data).

    **Expected Request:**
    - Content-Type: `multipart/form-data`
    - Required Field:
        - `image` (file): The image file to be analyzed.

    **Example Request (cURL):**
    ```
    curl -X POST http://localhost:8000/api/ai/images/analyse/ \
         -H "Authorization: Bearer <ACCESS_TOKEN>" \
         -F "image=@/path/to/image.jpg"
    ```

    **Expected Response:**
    - Status: `200 OK`
    - Content-Type: `application/json`
    - JSON Response Format:
    ```json
    {
        "detected_items": ["Steak", "Grilled Meat", "Garlic", "Herbs", "Lemon", "Lamb"]
    }
    ```
    - `detected_items`: `list[str]` – Detected food-related keywords.

    **TODO:**
    - Replace Mock Data with actual AI model integration.
    """
    if "image" not in request.FILES:
        return Response({"error": "No image uploaded"}, status=400)

    # Simulating AI processing time (Mock)
    time.sleep(1.5)

    # Mocked detected food items (Replace with actual AI model output)
    MOCK_DETECTED_ITEMS = ["Steak", "Grilled Meat", "Garlic", "Herbs", "Lemon", "Lamb"]


    return Response({
        "detected_items": MOCK_DETECTED_ITEMS
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, JSONParser])
def generate_caption(request):
    """
    Generate AI-powered captions
    """
    data = request.data.copy()

    image_file = request.FILES.get('image')

    categories = json.loads(data.get("categories", []))
    business_info = json.loads(data.get("business_info", {}))
    item_info = json.loads(data.get("item_info", []))
    detected_items = json.loads(data.get("detected_items", "[]"))
    
    additional_prompt = data.get("additional_prompt", "")
    include_sales_data = data.get("include_sales_data", 'false').lower() == 'true'

    try:
        business = Business.objects.get(owner=request.user)
        business_info["name"] = business.name
        business_info["type"] = business.category
    except Business.DoesNotExist:
        return Response({"error": "Business not found"}, status=404)

    image_url = None
    message_id = None
    # Upload image to Discord if provided
    if image_file:
        logger.debug("Uploading image to Discord for caption generation.")
        try:
            upload_result = upload_image_file_to_discord(image_file)
        except Exception as e:
            logger.error(f"Error uploading image to Discord: {str(e)}", exc_info=True)
            return Response({"error": "Failed to upload image to Discord"}, status=500)
        
        image_url = upload_result.get("image_url")
        message_id = upload_result.get("message_id")
        logger.debug(f"Image uploaded to Discord: {image_url}")

    try:
        captions = generate_captions(
            categories=categories,
            business_info=business_info,
            item_info=item_info,
            additional_prompt=additional_prompt,
            include_sales_data=include_sales_data,
            detected_items=detected_items,
            image_url=image_url,
        )
        return Response({"captions": captions}, status=200)
    except Exception as e:
        logger.error(f"Error generating captions: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=500)
    finally:
        if message_id:
            logger.debug("Deleting uploaded image from Discord.")
            delete_success = delete_discord_message(message_id)
            if delete_success:
                logger.debug("Image deleted from Discord successfully.")
            else:
                logger.error("Failed to delete image from Discord.")


