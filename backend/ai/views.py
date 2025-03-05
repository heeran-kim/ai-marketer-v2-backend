from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import time

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def analyse_image(request):
    """Upload image, save it, and return detected items."""
    if "image" not in request.FILES:
        return Response({"error": "No image uploaded"}, status=400)

    # TODO: CALL AI MODEL TO ANALYSE IMAGE
    time.sleep(1.5)
    MOCK_DETECTED_ITEMS = ["Steak", "Grilled Meat", "Garlic", "Herbs", "Lemon", "Lamb"]


    return Response({
        "detected_items": MOCK_DETECTED_ITEMS
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def generate_caption(request):
    """Generate AI-powered captions (Mock Data for now)"""

    # TODO: CALL AI MODEL TO GENERATE CAPTIONS
    time.sleep(1.5)
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
