from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView
from django.shortcuts import get_object_or_404
from posts.serializers import PostSerializer
from businesses.models import Business
from social.models import SocialMedia
from posts.models import Post
from config.constants import POST_CATEGORIES_OPTIONS, SOCIAL_PLATFORMS
import logging

logger = logging.getLogger(__name__)

class PostListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        business = Business.objects.filter(owner=self.request.user).first()
        if not business:
            return Post.objects.none()
        return Post.objects.filter(business=business).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serialized_posts = self.get_serializer(queryset, many=True).data

        response_data = {
            "posts": serialized_posts,
        }

        return Response(response_data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) # TODO
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        # TODO
        business = Business.objects.filter(owner=self.request.user).first()
        serializer.save(business=business)

    def get(self, request, *args, **kwargs):
        if request.query_params.get('create') == 'true':
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
                    "target_customers": business.target_customers,
                    "vibe": business.vibe,
                    "has_sales_data": False, # TODO
                },
                "post_categories": post_categories,
                "linked_platforms": linked_platforms,
            }

            return Response(response_data)

        return self.list(request, *args, **kwargs)

class PostDeleteView(APIView):
    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        post.delete()

        response_data = {"message": "Post deleted successfully."}

        return Response(response_data, status=200)
