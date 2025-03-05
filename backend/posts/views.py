from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from posts.serializers import PostSerializer
from businesses.models import Business
from social.models import SocialMedia
from posts.models import Post
from config.constants import POST_CATEGORIES_OPTIONS, SOCIAL_PLATFORMS

class PostListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        business = Business.objects.filter(owner=request.user).first()

        if not business:
            return Response({"error": "Business not found"}, status=404)

        posts = Post.objects.filter(business=business).order_by("-created_at")
        serialized_posts = PostSerializer(posts, many=True).data

        response_data = {
            "posts": serialized_posts,
        }

        return Response(response_data)

class PostCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        business = Business.objects.filter(owner=request.user).first()

        if not business:
            return Response({"error": "Business not found"}, status=404)

        post_categories = [
            {"id": index + 1, "label": category["label"], "selected": False}
            for index, category in enumerate(POST_CATEGORIES_OPTIONS)
        ]

        linked_platforms_queryset = SocialMedia.objects.filter(business=business)
        linked_platforms = [
            {
                "key": linked_platform.platform,
                "label": next(
                    (p["label"] for p in SOCIAL_PLATFORMS if p["key"] == linked_platform.platform),
                    linked_platform.platform
                ),
            }
            for linked_platform in linked_platforms_queryset
        ]

        response_data = {
            "business": {
                "target_customers": business.target,
                "vibe": business.vibe,
                "has_sales_data": False, # TODO
            },
            "post_categories": post_categories,
            "linked_platforms": linked_platforms,
        }

        return Response(response_data)