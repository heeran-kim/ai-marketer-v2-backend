from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import time

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
@parser_classes([JSONParser])
def generate_caption(request):
    """
    Generate AI-powered captions based on detected food items (Mock Data).

    **Expected Request:**
    - Content-Type: `application/json`
    - Required Fields:
        - `detected_items` (`list[str]`): List of food items detected in the image.
        - `business_info` (`dict`, optional): Additional details about the business.
        - `post_categories` (`list[str]`, optional): Categories related to the post.
        - `platform_states` (`dict`, optional): Information about which platforms the post will be published on.
        - `custom_text` (`str`, optional): Additional prompt to fine-tune the AI-generated caption.

    **Example Request (cURL):**
    ```
    curl -X POST http://localhost:8000/api/ai/captions/generate/ \
         -H "Authorization: Bearer <ACCESS_TOKEN>" \
         -H "Content-Type: application/json" \
         -d '{
                "detected_items": ["Steak", "Garlic", "Lemon"],
                "business_info": {"name": "Gourmet Steakhouse"},
                "post_categories": ["Food", "Fine Dining"],
                "platform_states": {"instagram": true, "facebook": false},
                "custom_text": "Luxury dining experience."
             }'
    ```

    **Expected Response:**
    - Status: `200 OK`
    - Content-Type: `application/json`
    - JSON Response Format:
    ```json
    {
        "captions": [
            "🔥 New Menu Alert! 🔥\nExperience the perfect balance of smoky grilled steak, fresh herbs, and a zesty lemon kick. 🍋🥩",
            "Indulge in perfection. 🥩✨\nJuicy, tender, and grilled to perfection – our newest menu item is here to elevate your dining experience."
        ]
    }
    ```
    - `captions`: `list[str]` – List of AI-generated captions.

    **TODO:**
    - Replace Mock Data with actual AI model integration.
    """

    # Simulating AI caption generation time (Mock)
    time.sleep(1.5)

    # Mocked AI-generated captions (Replace with actual AI model output)
    MOCK_GENERATED_CAPTIONS = [
        "🔥 New Menu Alert! 🔥\nExperience the perfect balance of smoky grilled steak, fresh herbs, and a zesty lemon kick. 🍋🥩 Our new menu is designed for true food lovers who crave bold flavors in a cozy, premium dining atmosphere. 🍷✨\n📍 Available now – tag your foodie friends and come try it! #NewMenu #SteakLover #PremiumDining",
        "Indulge in perfection. 🥩✨\nJuicy, tender, and grilled to perfection – our newest menu item is here to elevate your dining experience. A hint of garlic, fresh herbs, and a citrus twist make every bite unforgettable. 🍋🔥\nTag someone who needs to try this! #FoodieHeaven #SteakGoals #NewMenu",
        "New menu, who dis? 🥩🔥\nCrispy sear, juicy center, and that zesty lemon-garlic hit. You know you want it. 🍋💥\nPull up. #NewMenu #SteakDoneRight",
        "👀 Can you smell that? That’s the sound of your next favorite meal sizzling to perfection! 🥩🔥\nGarlic, herbs, and a squeeze of fresh lemon—simple, yet unforgettable. 🍋✨\nDrop a 🔥 in the comments if you’re craving this right now! #FoodieLife #SteakPerfection #NewOnTheMenu",
        "✨ A new flavor experience awaits! ✨\nOur latest menu addition combines the rich, smoky taste of perfectly grilled steak with a refreshing citrus twist and aromatic herbs. 🍽️ Whether you're here for a casual night out or a premium dining experience, this one’s for you! 🍷\nCome taste the difference. Reservations recommended! #NewMenu #SteakLover #DiningExperience"
    ];


    return Response({
        "captions": MOCK_GENERATED_CAPTIONS
    })
