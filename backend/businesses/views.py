from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.forms.models import model_to_dict
from businesses.models import Business
from social.models import SocialMedia
from social.serializers import SocialMediaSerializer
from posts.models import Post
from config.constants import DEFAULT_LOGO_URL, SOCIAL_PLATFORMS

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_dashboard_data(request):
    business = Business.objects.filter(owner=request.user).first()

    if not business:
        # Return consistent structure with null/empty values
        return Response({
            "business": None,
            "linkedPlatforms": [],
            "postsSummary": None
        })

    logo_url = getattr(business.logo, "url", DEFAULT_LOGO_URL)

    linked_platforms_queryset = SocialMedia.objects.filter(business=business)
    linked_platforms = SocialMediaSerializer(linked_platforms_queryset, many=True).data

    posts = Post.objects.filter(business=business)
    last_post = posts.order_by("-created_at").first()

    posts_summary = {
        "upcomingPosts": posts.filter(status="upcoming").count(),
        "uploadedPosts": posts.filter(status="uploaded").count(),
        "failedPosts": posts.filter(status="failed").count(),
        "lastActivity": last_post.created_at.strftime("%Y-%m-%d %H:%M:%S") if last_post else None,
        "lastPostLink": getattr(last_post, "link", None) if last_post else None,
    }

    response_data = {
        "business": {
            "name": business.name,
            "logo": logo_url,
        },
        "linkedPlatforms": linked_platforms,
        "postsSummary": posts_summary,
    }

    return Response(response_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_business_data(request):
    """Fetches business details of the authenticated user, returns empty values if no business is found."""
    business = Business.objects.filter(owner=request.user).first()

    if not business:
        # Return a structured response with null/empty values instead of an error.
        return Response({
            "name": None,
            "logo": DEFAULT_LOGO_URL,
            "category": None,
            "target": None,
            "vibe": None
        }, status=200)  # Keep 200 status for a successful request.

    business_data = model_to_dict(business)

    business_data["logo"] = business.logo.url if business.logo else DEFAULT_LOGO_URL

    return Response(business_data)