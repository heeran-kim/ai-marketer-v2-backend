from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from businesses.models import Business
from social.models import SocialMedia
from posts.models import Post
from posts.serializers import PostSerializer
from config.constants import POST_CATEGORIES_OPTIONS, SOCIAL_PLATFORMS

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def show(request):
    business = Business.objects.filter(owner=request.user).first()

    if not business:
        return Response({"error": "Business not found"}, status=404)

    posts = Post.objects.filter(business=business).order_by("-created_at")
    serialized_posts = PostSerializer(posts, many=True).data

    response_data = {
        "posts": serialized_posts,
    }

    return Response(response_data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def create(request):
    business = Business.objects.filter(owner=request.user).first()

    if not business:
        return Response({"error": "Business not found"}, status=404)

    post_categories = [
        {"id": index + 1, "label": category["label"], "selected": False}  # ✅ id 추가
        for index, category in enumerate(POST_CATEGORIES_OPTIONS)
    ]

    platform_options = [platform["label"] for platform in SOCIAL_PLATFORMS]

    social_media_platforms = SocialMedia.objects.filter(business=business)
    platform_states = [
        {
            "label": next((p["label"] for p in SOCIAL_PLATFORMS if p["key"] == social.platform), social.platform),
            "account": social.username,
            "selected": False,
            "caption": "",
        }
        for social in social_media_platforms
    ]

    response_data = {
        "business": {
            "target": business.target,
            "vibe": business.vibe,
            "salesDataEnabled": False,
        },
        "postCategories": post_categories,
        "platformOptions": platform_options,
        "platformStates": platform_states,
    }

    return Response(response_data)