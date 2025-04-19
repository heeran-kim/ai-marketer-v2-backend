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
import requests
import os
from PIL import Image
import io

from cryptography.fernet import Fernet #cryptography package

TWOFA_ENCRYPTION_KEY = os.getenv("TWOFA_ENCRYPTION_KEY")
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")

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
    
    def get_facebook_page_id(self,access_token):
        #Retrieve facebook page id data from Meta's API
        url = f'https://graph.facebook.com/v22.0/me/accounts?access_token={access_token}'
        response = requests.get(url)
        #return Response({'message':response,'access_token':access_token,'status':status.HTTP_200_OK})
        if response.status_code != 200:
            # Handle error response    
            return None
        metasData = response.json()
        if not metasData.get("data"):
            return None
        #else return the page id
        return metasData.get("data")[0]["id"]
    
    def returnInstagramDetails(self,facebookPageID,access_token):
        url = f'https://graph.facebook.com/v22.0/{facebookPageID}?fields=instagram_business_account&access_token={access_token}'
        response = requests.get(url)
        data=response.json()
        if response.status_code != 200:
            # Handle error retrieving insta account id   
            return None
        insta_account_data = data.get("instagram_business_account")
        if not insta_account_data:
            return None #return error if no instagram account found
        return insta_account_data.get("id") #return the instagram account id
    
    def crop_center_resize(self, image, target_width=1080, target_height=1350):
        aspect_target = target_width / target_height
        width, height = image.size
        aspect_original = width / height

        # Crop to match aspect ratio
        if aspect_original > aspect_target:
            # Too wide — crop sides
            new_width = int(height * aspect_target)
            left = (width - new_width) // 2
            right = left + new_width
            top, bottom = 0, height
        else:
            # Too tall — crop top/bottom
            new_height = int(width / aspect_target)
            top = (height - new_height) // 2
            bottom = top + new_height
            left, right = 0, width

        cropped = image.crop((left, top, right, bottom))
        resized = cropped.resize((target_width, target_height), Image.LANCZOS)
        return resized
    
    def publishToMeta(self, platform, caption, image_file, user):
        f = Fernet(TWOFA_ENCRYPTION_KEY) 
        token=user.access_token[1:]  #do 1: to not include byte identifier
        token_decrypted=f.decrypt(token)
        token_decoded=token_decrypted.decode()

        facebookPageID=self.get_facebook_page_id(token_decoded)
        if not facebookPageID:
            return {"error": "Unable to retrieve Facebook Page ID", "status": False}
        # Get the Instagram account ID
        instagram_account_id = self.returnInstagramDetails(facebookPageID,token_decoded)
        if not instagram_account_id:    
            return {"error": "Unable to retrieve Insta ID", "status": False}

        #Get Image setup
        headers = {
            'Authorization': f'Client-ID {IMGUR_CLIENT_ID}',
        }
        #image_file.file.seek(0)
        img = Image.open(image_file)
        img = self.crop_center_resize(img) # 4:5 portrait
        # Save to in-memory buffer
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        files = {'image': ('image.jpg', buffer, 'image/jpeg')}
        response = requests.post(
            'https://api.imgur.com/3/image',
            headers=headers,
            files=files
        )
        if response.status_code != 200:
            return {"error": f"Unable to upload to Imgur | text:{response.text}", "status": False}
        image_url = response.json()['data']['link']
        alt_text="This is the alt text for the image"

        #Create media object
        url = f'https://graph.facebook.com/v22.0/{instagram_account_id}/media'
        data = {
            "image_url": image_url,
            "caption": caption,
            "alt_text": alt_text,
            "access_token": token_decoded
        }
        response = requests.post(url, data=data)
        if response.status_code != 200:
            # Handle error response
            return {"error": f"Unable to create Media Obj | text:{response.text} link:{image_url} caption={caption}", "status": False}
        media_data = response.json()
        if not media_data.get("id"):
            return {"error": "Unable to retrieve media ID", "status": False}
        media_id = media_data.get("id")

        #Publish the media object
        url = f'https://graph.facebook.com/v22.0/{instagram_account_id}/media_publish?creation_id={media_id}&access_token={token_decoded}'
        response = requests.post(url)
        if response.status_code != 200:
            # Handle error response
            return {"error": "Unable to publish media obj", "status": False}
        publish_data = response.json()
        if not publish_data.get("id"):
            return {"error": "Unable to retrieve publish ID", "status": False}
        post_id = publish_data.get("id")
        # Return the post ID
        return {"message": {post_id}, "status": True}


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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

        match data["platform"]:
            case 'facebook':
                return Response({"error": "Not implemented"}, status=status.HTTP_400_BAD_REQUEST)
            case 'instagram':
                response = self.publishToMeta('instagram',data.get("caption", ""),request.FILES.get('image'), request.user)
                if (response.get("status") == False):
                    return Response({"error": response.get("error")}, status=status.HTTP_400_BAD_REQUEST)   #Then no post id was provided
                # post.link = f'https://www.instagram.com/p/{response.get("message")}/'
                # post.save()
            case 'twitter':
                return Response({"error": "Not implemented"}, status=status.HTTP_400_BAD_REQUEST)
            case _:
                return Response({"error": "Invalid platform"}, status=status.HTTP_400_BAD_REQUEST)
        
        # return Response({"message": "Post not created successfully!"}, status=status.HTTP_400_BAD_REQUEST)
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
