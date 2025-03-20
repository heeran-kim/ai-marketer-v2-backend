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
from config.constants import DEFAULT_LOGO_URL


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
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
                "logo": DEFAULT_LOGO_URL,
                "category": None,
                "target_customers": None,
                "vibe": None
            }, status=status.HTTP_200_OK)

        serializer = BusinessSerializer(business)
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

        # Regular field update or creation
        if not business:
            serializer = BusinessSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(owner=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            serializer = BusinessSerializer(business, data=request.data, partial=partial)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _validate_logo_file(self, logo_file):
        """Validate logo file size and type."""
        # Validation logic here...
        return True, None