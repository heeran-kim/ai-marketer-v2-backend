# backend/businesses/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Business
from .serializers import BusinessSerializer
from social.models import SocialMedia
from social.serializers import SocialMediaSerializer
from posts.models import Post
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business = Business.objects.filter(owner=request.user).first()

        if not business:
            # Return consistent structure with null/empty values
            return Response({
                "business": None,
                "linked_platforms": [],
                "posts_summary": None
            })

        logo_field = business.logo
        if not logo_field:
            logo_path = 'defaults/default_logo.png'
        else:
            logo_path = logo_field

        linked_platforms = []
        platforms = SocialMedia.objects.filter(business=business)

        for platform in platforms:
            published_count = Post.objects.filter(
                business=business,
                platform=platform,
                status="Published"
            ).count()

            linked_platforms.append({
                "key": platform.platform,
                "label": platform.get_platform_display(),
                "link": platform.link,
                "username": platform.username,
                "num_published": published_count,
            })

        posts = Post.objects.filter(business=business)

        posts_summary = {
            "num_scheduled": posts.filter(status="Scheduled").count(),
            "num_published": posts.filter(status="Published").count(),
            "num_failed": posts.filter(status="Failed").count(),
        }

        from collections import defaultdict
        published_posts = posts.filter(status="Published").order_by("-posted_at")
        
        platforms_by_datetime = defaultdict(list)
        for post in published_posts:
            date_str = post.posted_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            platforms_by_datetime[date_str].append(post.platform.platform)
        
        last_post_date = published_posts.first().posted_at.isoformat() if published_posts.exists() else None

        business_serializer = BusinessSerializer(business, context={'request': request})

        response_data = {
            "business": business_serializer.data,
            "linked_platforms": linked_platforms,
            "posts_summary": posts_summary,
            "post_activity": {
                "platforms_by_datetime": platforms_by_datetime,
                "last_post_date": last_post_date,
            }
        }

        return Response(response_data)


class BusinessDetailView(APIView):
    """
    API view for retrieving and updating business details.
    GET: Retrieve the authenticated user's business.
    PUT/PATCH: Update the business details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve business details for the authenticated user."""
        business = Business.objects.filter(owner=request.user).first()

        if not business:
            # Return structured empty response
            return Response({
                "name": None,
                "logo": None,
                "category": None,
                "target_customers": None,
                "vibe": None
            }, status=status.HTTP_200_OK)

        serializer = BusinessSerializer(business, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        """Update business details fully or create if doesn't exist."""
        return self._update_business(request)

    def patch(self, request):
        """Update business details partially."""
        return self._update_business(request, partial=True)

    def _update_business(self, request, partial=False):
        """Helper method for update operations."""
        business = Business.objects.filter(owner=request.user).first()

        # Handle file upload
        if 'logo' in request.FILES:
            logo_file = request.FILES['logo']
            is_valid, error_message = self._validate_logo_file(logo_file)
            if not is_valid:
                return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

            # Logo-only update or creation
            if not business:
                business = Business(owner=request.user)
                business.logo = logo_file
                business.save()
                return Response({"message": "Business created with logo"}, status=status.HTTP_201_CREATED)
            else:
                business.logo = logo_file
                business.save(update_fields=['logo'])
                return Response({"message": "Logo updated successfully"}, status=status.HTTP_200_OK)

        if request.data.get('logo_removed') == 'true' and business:
            if business.logo:
                business.logo.delete(save=False)

            business.logo = None
            business.save(update_fields=['logo'])
            return Response({"message": "Logo removed successfully"}, status=status.HTTP_200_OK)

        # Regular field update or creation
        if not business:
            serializer = BusinessSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(owner=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            serializer = BusinessSerializer(business, data=request.data, partial=partial, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _validate_logo_file(self, logo_file):
        """Validate logo file size and type."""
        # Validation logic here...
        return True, None