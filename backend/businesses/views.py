# backend/businesses/views.py
from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets
from rest_framework.decorators import action
from config import settings
from utils.square_api import exchange_code_for_token, get_auth_url_values, get_square_client, get_square_locations, format_square_item
from .models import Business
from .serializers import BusinessSerializer
from social.models import SocialMedia
from posts.models import Post
import uuid
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
    

class SquareViewSet(viewsets.ViewSet):
    """
    ViewSet for managing Square integration.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Check if Square integration is connected for the authenticated user's business."""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)

        client = get_square_client(business)
        if not client:
            return Response({"square_connected": False, "business_name": None})
        
        locations = get_square_locations(client)
        if not locations:
            return Response({"square_connected": True, "business_name": None})
        
        return Response({
            "square_connected": True,
            "business_name": locations[0].get("name")
        })

    @action(detail=False, methods=['post'])
    def connect(self, request):
        """Connect Square integration for the authenticated user's business."""
        auth_url_values = get_auth_url_values()
        request.session['square_oauth_state'] = auth_url_values['state']

        auth_url = (
            f"{settings.SQUARE_BASE_URL}/oauth2/authorize"
            f"?client_id={auth_url_values['app_id']}"
            f"&scope=MERCHANT_PROFILE_READ+ITEMS_READ+ITEMS_WRITE+ORDERS_READ"
            f"&session=false&state={auth_url_values['state']}"
            f"&redirect_uri={auth_url_values['redirect_uri']}"
        )
        
        return Response({"link": auth_url}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def callback(self, request):
        """Create Square integration for the authenticated user's business."""
        received_state = request.query_params.get('state')
        saved_state = request.session.get('square_oauth_state')

        # Ensure state matches and prevent CSRF
        if not saved_state or received_state != saved_state:
            return redirect(f"{settings.FRONTEND_BASE_URL}/settings/square?error=state_mismatch")        
        error = request.query_params.get('error')
        
        # Handle error scenarios
        if error:
            error_description = request.query_params.get('error_description')
            if ('access_denied' == error and 'user_denied' == error_description):
                return redirect(f"{settings.FRONTEND_BASE_URL}/settings/square?error=user_denied")
            else:
                return redirect(f"{settings.FRONTEND_BASE_URL}/settings/square?error=${error}&error_description=${error_description}")
            
        # Get the authorization code
        code = request.query_params.get('code')
        if not code:
            return redirect(f"{settings.FRONTEND_BASE_URL}/settings/square?error=missing_code")

        # Exchange code for access token
        token_response = exchange_code_for_token(code)
        if 'access_token' not in token_response:
            logger.info(f"Error: {token_response}")
            return redirect(f"{settings.FRONTEND_BASE_URL}/settings/square?error=token_error")

        # Save the access token to the business
        access_token = token_response['access_token']
        business = Business.objects.filter(owner=request.user).first()
        business.square_access_token = access_token
        business.save()
        logger.info(f"Square access token: {access_token}")

        # After successful connection, pop the state from the session
        request.session.pop('square_oauth_state', None)
        
        return redirect(f"{settings.FRONTEND_BASE_URL}/settings/square?success=true")
    
    @action(detail=False, methods=['post'])
    def disconnect(self, request):
        """Disconnect Square integration for the authenticated user's business."""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Remove the access token and disconnect the business
        business.square_access_token = None
        business.save()
        
        return Response({"message": "Square integration deleted successfully"}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='items')
    def list_items(self, request):
        """Retrieve items from Square for the authenticated user's business."""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)

        client = get_square_client(business)
        if not client:
            return Response({"error": "Square not connected"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Get catalog items
            catalog_api = client.catalog
            
            # Get categories
            categories_response = catalog_api.list_catalog(
                cursor=None,
                types=["CATEGORY"]
            )
            
            categories = []
            if categories_response.is_success():
                for obj in categories_response.body.get("objects", []):
                    if obj.get("type") == "CATEGORY" and "category_data" in obj:
                        categories.append({
                            "id": obj["id"],
                            "name": obj["category_data"]["name"]
                        })
            
            # Get items
            items_response = catalog_api.list_catalog(
                cursor=None,
                types=["ITEM"]
            )

            items = []
            if items_response.is_success():
                for obj in items_response.body.get("objects", []):
                    item = format_square_item(obj)
                    if item:
                        items.append(item)
            
            return Response({
                "items": items,
                "categories": categories
            })
        
        except Exception as e:
            logger.error(f"Square items fetch error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['patch'], url_path='items/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """Update a menu item in Square."""
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
        
        client = get_square_client(business)
        if not client:
            return Response({"error": "Square not connected"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            catalog_api = client.catalog

            item_response = catalog_api.retrieve_catalog_object(object_id=item_id, include_related_objects=True)
            latest_version = item_response.body["object"]["version"]
            logger.info(f"Latest version of item {item_id}: {latest_version}")

            related_objects = item_response.body.get("related_objects", [])
            variation_versions = {
                obj["id"]: obj["version"]
                for obj in related_objects if obj["type"] == "ITEM_VARIATION"
            }

            raw_variations = request.data.get("variations", [])
            formatted_variations = [
                {
                    "type": "ITEM_VARIATION",
                    "id": v["id"],
                    "version": variation_versions.get(v["id"]),
                    "item_variation_data": {
                        "item_id": item_id,
                        "name": v["name"],
                        "pricing_type": "FIXED_PRICING",
                        "price_money": v["price_money"]
                    }
                }
                for v in raw_variations
            ]

            updated_item = {
                "idempotency_key": str(uuid.uuid4()),
                "object": {
                    "type": "ITEM",
                    "id": item_id,
                    "version": latest_version,
                    "item_data": {
                        "name": request.data.get("name"),
                        "description": request.data.get("description", ""),
                        "variations": formatted_variations,
                    }
                }
            }
            
            update_response = catalog_api.upsert_catalog_object(body=updated_item)

            if update_response.is_success():
                logger.info(f"Item {item_id} and its variations updated successfully.")
                return Response({
                    "message": f"Item {item_id} updated successfully.",
                    "item": update_response.body
                }, status=status.HTTP_200_OK)
            else:
                logger.error(f"Failed to update item {item_id}: {update_response.errors}")
                return Response({"error": update_response.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Square item update error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        