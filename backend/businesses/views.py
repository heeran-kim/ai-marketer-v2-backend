from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.forms.models import model_to_dict
from businesses.models import Business
from social.models import SocialMedia
from posts.models import Post
from config.constants import DEFAULT_LOGO_URL

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_dashboard_data(request):
    business = Business.objects.filter(owner=request.user).first()

    if not business:
        return Response({"error": "Business not found"}, status=404)

    logo_url = getattr(business.logo, "url", DEFAULT_LOGO_URL)

    social_media = SocialMedia.objects.filter(business=business)
    social_media_data = [
        {
            "platform": sm.platform,
            "link": sm.link,
            "username": sm.username,
        }
        for sm in social_media
    ]

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
        "socialMedia": social_media_data,
        "postsSummary": posts_summary,
    }

    return Response(response_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_business_data(request):
    business = Business.objects.filter(owner=request.user).first()

    if not business:
        return Response({"error": "Business not found"}, status=404)

    business_data = model_to_dict(business)

    business_data["logo"] = business.logo.url if business.logo else DEFAULT_LOGO_URL

    return Response(business_data)