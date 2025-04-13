import json
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView
from django.utils import timezone
from itertools import chain
from promotions.models import Promotion
from posts.serializers import PostSerializer
from businesses.models import Business
from social.models import SocialMedia
from posts.models import Post, Category
from config.constants import POST_CATEGORIES_OPTIONS, SOCIAL_PLATFORMS
from utils.square_api import check_square_integration
import logging

logger = logging.getLogger(__name__)

class PostListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        business = Business.objects.filter(owner=self.request.user).first()
        if not business:
            return Post.objects.none()

        failed_posts = list(Post.objects.filter(
            business=business,
            status='Failed'
        ).order_by('-created_at'))

        scheduled_posts = list(Post.objects.filter(
            business=business,
            status='Scheduled'
        ).order_by('-scheduled_at'))

        posted_posts = list(Post.objects.filter(
            business=business,
            status='Published'
        ).order_by('-posted_at'))

        combined_posts = list(chain(failed_posts, scheduled_posts, posted_posts))
        return combined_posts

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

            selectable_categories = [
                {"id": index + 1, "label": category["label"], "is_selected": False}
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

            square_integration_status = {
                "hasPOSIntegration": False,
                "hasSalesData": False,
                "hasItemsInfo": False,
                "items": [],
                }
            
            logger.debug(f"Checking Square integration for business: {business.id}")
            try: 
                square_integration_status = check_square_integration(business)
                logger.debug(f"Square integration status: {square_integration_status}")
            except Exception as e:
                logger.error(f"Error checking Square integration: {e}")

            response_data = {
                "business": {
                    "target_customers": business.target_customers,
                    "vibe": business.vibe,
                    "hasPOSIntegration": square_integration_status["hasPOSIntegration"],
                    "hasItemsInfo": square_integration_status["hasItemsInfo"],
                    "hasSalesData": square_integration_status["hasSalesData"],
                    "items": square_integration_status["items"],
                },
                "selectable_categories": selectable_categories,
                "linked_platforms": linked_platforms,
            }

            logger.info(f"Response data for business {business.id}: {response_data}")
            return Response(response_data)

        return self.list(request, *args, **kwargs)
    
    def post(self, request):
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle file upload
        if 'image' not in request.FILES:
            return Response({"error": "No Image provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.POST

        try:
            platform = SocialMedia.objects.get(platform=data["platform"])
        except SocialMedia.DoesNotExist:
            return Response({"error": "Invalid platform"}, status=status.HTTP_400_BAD_REQUEST)
        
        promotion = None
        if "promotion" in data and data["promotion"]:
            try:
                promotion = Promotion.objects.get(id=data["promotion"])
            except Promotion.DoesNotExist:
                return Response({"error": "Invalid promotion ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        scheduled_at = data.get("scheduled_at")
        if scheduled_at:
            posted_at = None
            link = None
            post_status = "Scheduled"
        else :
            # TODO
            scheduled_at = None
            posted_at = timezone.now()
            link = "test.com"
            post_status = "Published"

        
        post = Post.objects.create(
            business=business,
            platform=platform,
            caption=data.get("caption", ""),
            image=request.FILES.get('image'),
            link=link,
            posted_at=posted_at,
            scheduled_at=scheduled_at,
            status=post_status,
            promotion=promotion
        )
        
        categories_data = json.loads(data.get("categories", "[]"))
        categories = Category.objects.filter(id__in=categories_data)
        post.categories.set(categories)

        return Response({"message": "Post created successfully!"}, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    """
    API view for retrieving, updating and deleting a specific post.
    """
    permission_classes = [IsAuthenticated]

    def get_post(self, pk, user):
        """Helper method to get a post and verify ownership"""
        business = Business.objects.filter(owner=user).first()
        if not business:
            return None, Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            post = Post.objects.get(pk=pk, business=business)
            return post, None
        except Post.DoesNotExist:
            return None, Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        """Retrieve a specific post"""
        post, error_response = self.get_post(pk, request.user)
        if error_response:
            return error_response

        serializer = PostSerializer(post)
        return Response(serializer.data)

    def patch(self, request, pk):
        """Update a post partially"""
        post, error_response = self.get_post(pk, request.user)
        if error_response:
            return error_response

        # Handle caption updates
        if 'caption' in request.data:
            post.caption = request.data['caption']

        # Handle categories updates
        if 'categories' in request.data:
            # First clear existing categories
            post.categories.clear()
            # Then add new categories
            category_labels = request.data.getlist('categories')
            for label in category_labels:
                try:
                    category = Category.objects.get(label=label)
                except Category.DoesNotExist:
                    return Response({"error": f"Category '{label}' does not exist."}, status=400)
                post.categories.add(category)

        # Handle image updates if provided
        if 'image' in request.FILES:
            post.image = request.FILES['image']

        # Handle scheduled_at updates
        if 'scheduled_at' in request.data:
            scheduled_at = request.data.get("scheduled_at")

            if scheduled_at:
                post.scheduled_at = scheduled_at
                post.status = 'Scheduled'
            else:
                post.scheduled_at = None
                try:
                    # TODO success = publish_to_social_media(post)
                    success = True
                    post.link = "https://test.com/p/test"

                    if success:
                        post.status = 'Published'
                        post.posted_at = timezone.now()
                    else:
                        post.status = 'Failed'
                except Exception as e:
                    logger.error(f"Error publishing post: {e}")
                    post.status = 'Failed'

        post.save()

        serializer = PostSerializer(post)
        return Response(serializer.data)

    def delete(self, request, pk):
        """Delete a post"""
        post, error_response = self.get_post(pk, request.user)
        if error_response:
            return error_response

        post.delete()
        return Response({"message": "Post deleted successfully"}, status=status.HTTP_200_OK)
