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
from utils.square_api import get_square_summary
import logging
import requests
import os
from PIL import Image
import io
from datetime import datetime
from zoneinfo import ZoneInfo

from datetime import datetime, timedelta
from config.celeryTasks import publish_to_meta_task,publishToMeta

from django.core.files import File

from cryptography.fernet import Fernet #cryptography package
from django.db.models import Q,Count

TWOFA_ENCRYPTION_KEY = os.getenv("TWOFA_ENCRYPTION_KEY")
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")

logger = logging.getLogger(__name__)

class PostListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def get_meta_posts(self, user, platform):
        #Get Access Token
        token_decoded = self.get_user_access_token(user)
        #Get Facebook page id
        facebookPageID=self.get_facebook_page_id(token_decoded)
        if not facebookPageID:
            return {"error": "Unable to retrieve Facebook Page ID! Maybe reconnect your Facebook or Instagram account in Settings!", "status": False}
        
        #For Facebook
        if platform == 'facebook':
            #Get page access token
            url = f'https://graph.facebook.com/v22.0/me/accounts?access_token={token_decoded}'
            response = requests.get(url)
            if response.status_code != 200:
                # Handle error response
                return {"error": f"Unable to retrieve page access token. {response.text}", "status": False}
            metasData = response.json()
            if not metasData.get("data"):
                return {"error": "Unable to retrieve page access token 2", "status": False}
            #Get the page access token
            page_access_token = metasData.get("data")[0]["access_token"]
            url = f'https://graph.facebook.com/v22.0/{facebookPageID}/posts?fields=id,message,created_time,permalink_url,full_picture,likes.summary(true),comments.summary(true)&access_token={page_access_token}'
            response = requests.get(url)
            if response.status_code != 200:
                # Handle error response
                return {"error": f"Unable to fetch posts. {response.text}", "status": False}
            media_data = response.json()
            if not media_data.get("data"):
                return {"error": f"Unable to retrieve posts {response.text}", "status": False}
            posts_data = media_data.get("data")
            return {"message": posts_data, "status": True}
        
        #For Instagram
        # Get the Instagram account ID
        instagram_account_id = self.returnInstagramDetails(facebookPageID,token_decoded)
        if not instagram_account_id:    
            return {"error": "Unable to retrieve Insta ID", "status": False}
        #Send request to Meta API to get posts
        url = f'https://graph.facebook.com/v22.0/{instagram_account_id}/media?fields=id,caption,media_type,media_url,timestamp,permalink,thumbnail_url,children,like_count,comments&access_token={token_decoded}'
        response = requests.get(url)
        if response.status_code != 200:
            # Handle error response
            return {"error": f"Unable to fetch posts. {response.text}", "status": False}
        media_data = response.json()
        if not media_data.get("data"):
            return {"error": f"Unable to retrieve posts {response.text}", "status": False}
        posts_data = media_data.get("data")
        return {"message": posts_data, "status": True}
    
    def save_meta_image(self, post_data, save_path,platform):
        media_type=post_data.get('media_type') if platform=="instagram" else "IMAGE" #Image for facebook
        image_url=None
        if media_type == "IMAGE" or media_type == "CAROUSEL_ALBUM":
            image_url = post_data.get('media_url') if platform == "instagram" else post_data.get('full_picture')
        elif media_type == "VIDEO" and platform == "instagram":
            image_url = post_data.get('thumbnail_url')
        else:
            return "/app/media/No_Image_Available.jpg"
        # Download the image and save it
        response = requests.get(image_url)

        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return save_path
        else:
            return "/app/media/No_Image_Available.jpg"

    def remove_deleted_posts(self,platform,posts_data,business):
        platform_obj = SocialMedia.objects.get(platform=platform)

        # Collect all links you want to match against
        links = [
            post_data.get("permalink") if platform == 'instagram' else post_data.get("permalink_url")
            for post_data in posts_data
        ]

        # Fetch posts for the business and platform where link is NOT in the list
        posts_not_in_links = Post.objects.filter(
            business=business,
            platform=platform_obj
        ).exclude(
            link__in=links
        )

        for post in posts_not_in_links:
            if(post.status!="Scheduled"):
                post.delete()

        #Collect Duplicates and delete scheduled post in replacement of published one
        duplicates = (
            Post.objects
            .values('caption', 'scheduled_at')
            .annotate(dupe_count=Count('id'))
            .filter(dupe_count__gt=1)
        )
        q_filter = Q()
        for entry in duplicates:
            q_filter |= Q(caption=entry['caption'], scheduled_at=entry['scheduled_at'])

        posts_with_same_caption_and_time = Post.objects.filter(q_filter)

        for post in posts_with_same_caption_and_time:
            if(post.status=="Scheduled"):
                post.delete()
        
    def meta_get_function(self, business, platform):
        #Save posts to the database
        get_posts = self.get_meta_posts(self.request.user,platform)
        if get_posts.get("status") == False:
            logger.error(f"Error fetching posts: {get_posts.get('error')}")
            return Post.objects.none()
        posts_data = get_posts.get("message")

        #Check if it was a reset by the user - Not used
        # param = self.request.GET.get('status', None)
        # logger.error(f"Param {param}")

        self.remove_deleted_posts(platform,posts_data,business)

        for post_data in posts_data:
            # Check if the post already exists in the database and update reactions
            link=post_data.get("permalink") if platform=='instagram' else post_data.get("permalink_url")
            if Post.objects.filter(business=business, platform=SocialMedia.objects.get(platform=platform), link=link).exists():
                found_post=Post.objects.filter(business=business, platform=SocialMedia.objects.get(platform=platform), link=link).first()
                comments = post_data.get("comments", 0)
                comment_count=len(post_data.get("comments").get("data")) if comments else 0
                found_post.comments= comment_count #if platform=='instagram' else post_data.get('comments').get('summary').get('total_count') not working
                
                found_post.reactions=post_data.get("like_count", 0) if platform=='instagram' else post_data.get('likes').get('summary').get('total_count')
                found_post.save()
                continue
            # Create a new Post object
            file_path= self.save_meta_image(post_data,f"/app/media/business_posts/{business.id}/{post_data.get('id')}.jpg",platform)
            comments= post_data.get("comments", 0)
            comment_count=len(post_data.get("comments").get("data")) if comments else 0

            with open(file_path, 'rb') as f:
                django_file = File(f)
                post = Post(
                    business=business,
                    platform=SocialMedia.objects.get(platform=platform),
                    caption=post_data.get("caption") if platform=='instagram' else post_data.get("message"),
                    link=link,
                    post_id=post_data.get("id"),
                    posted_at=post_data.get("timestamp") if platform=='instagram' else post_data.get("created_time"),
                    image=django_file,
                    scheduled_at=None,
                    status='Published',
                    promotion=None,
                    reactions=post_data.get("like_count", 0) if platform=='instagram' else post_data.get('likes').get('summary').get('total_count'),
                    comments=comment_count #if platform=='instagram' else post_data.get('comments').get('summary').get('total_count') not working atm
                )
                # Save the post to the database
                post.save()


    def get_queryset(self):
        business = Business.objects.filter(owner=self.request.user).first()
        if not business:
            return Post.objects.none()
        
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

        # Check if the business is linked to Facebook
        if any(platform["key"] == "facebook" for platform in linked_platforms):
            self.meta_get_function(business,'facebook')
        # Check if the business is linked to Instagram
        if any(platform["key"] == "instagram" for platform in linked_platforms):
            # Get posts from Meta API
            self.meta_get_function(business,'instagram')

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

        return Response(response_data, status=status.HTTP_200_OK)
    
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

        #Crop to match aspect ratio
        if aspect_original > aspect_target:
            #If too wide — crop sides
            new_width = int(height * aspect_target)
            left = (width - new_width) // 2
            right = left + new_width
            top, bottom = 0, height
        else:
            #If too tall — crop top/bottom
            new_height = int(width / aspect_target)
            top = (height - new_height) // 2
            bottom = top + new_height
            left, right = 0, width

        cropped = image.crop((left, top, right, bottom))
        resized = cropped.resize((target_width, target_height), Image.LANCZOS)
        return resized
    
    def get_user_access_token(self, user):
        f = Fernet(TWOFA_ENCRYPTION_KEY) 
        token=user.access_token[1:]  #do 1: to not include byte identifier
        token_decrypted=f.decrypt(token)
        token_decoded=token_decrypted.decode()
        return token_decoded

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        # TODO
        business = Business.objects.filter(owner=self.request.user).first()
        serializer.save(business=business)

    def upload_image_file(self,image_file,aspectRatio):
        #Get Image setup
        headers = {
            'Authorization': f'Client-ID {IMGUR_CLIENT_ID}',
        }

        #image_file.file.seek(0)
        img = Image.open(image_file)
        if(aspectRatio == "1/1"):
            img = self.crop_center_resize(img,1080,1080) # 1:1 portrait
        else:
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
        return image_url

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
                "square_connected": False,
                "items": [],
                }
            
            logger.debug(f"Checking Square integration for business: {business.id}")
            try: 
                square_integration_status = get_square_summary(business)
                logger.debug(f"Square integration status: {square_integration_status}")
            except Exception as e:
                logger.error(f"Error checking Square integration: {e}")

            response_data = {
                "business": {
                    "target_customers": business.target_customers,
                    "vibe": business.vibe,
                    "square_connected": square_integration_status["square_connected"],
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

        image_url=self.upload_image_file(request.FILES.get('image'),data.get("aspect_ratio","4/5"))
        access_token=self.get_user_access_token(request.user)

        match data["platform"]:
            case 'facebook':
                #Schedule post
                if scheduled_at:
                    dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                    publish_to_meta_task.apply_async(args=["facebook", data.get("caption", ""),image_url,access_token],eta=dt)
                    link="Not published yet!"
                #Else post straight away
                else:
                    response = publishToMeta("facebook", data.get("caption", ""),image_url,access_token)
                    if (response.get("status") == False):
                        return Response({"error": response.get("error")}, status=status.HTTP_400_BAD_REQUEST)   #Then no post id was provided
                    link=response.get("message")
            case 'instagram':
                #Schedule post
                if scheduled_at:
                    dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                    publish_to_meta_task.apply_async(args=["instagram", data.get("caption", ""),image_url,access_token],eta=dt)
                    link="Not published yet!"
                #Else post straight away
                else:
                    response = publishToMeta("instagram", data.get("caption", ""),image_url,access_token)
                    if (response.get("status") == False):
                        return Response({"error": response.get("error")}, status=status.HTTP_400_BAD_REQUEST)   #Then no post id was provided
                    link=response.get("message")
            case 'twitter':
                return Response({"error": "Not implemented"}, status=status.HTTP_400_BAD_REQUEST)
            case _:
                return Response({"error": "Invalid platform"}, status=status.HTTP_400_BAD_REQUEST)
        

        #Now create post object on backend here if successfully published/scheduled
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
        
    def get_meta_comments(self,user,platform):
        #Get Access Token
        token_decoded = self.get_user_access_token(user)
        #Get Facebook page id
        facebookPageID=self.get_facebook_page_id(token_decoded)
        if not facebookPageID:
            return {"error": "Unable to retrieve Facebook Page ID! Maybe reconnect your Facebook or Instagram account in Settings!", "status": False}
        
        #For Facebook
        if platform == 'facebook':
            #Get page access token
            url = f'https://graph.facebook.com/v22.0/me/accounts?access_token={token_decoded}'
            response = requests.get(url)
            if response.status_code != 200:
                # Handle error response
                return {"error": f"Unable to retrieve page access token. {response.text}", "status": False}
            metasData = response.json()
            if not metasData.get("data"):
                return {"error": "Unable to retrieve page access token 2", "status": False}
            #Get the page access token
            page_access_token = metasData.get("data")[0]["access_token"]
            url = f'https://graph.facebook.com/v22.0/{facebookPageID}/posts?fields=id,comments.summary(true)&access_token={page_access_token}'
            response = requests.get(url)
            if response.status_code != 200:
                # Handle error response
                return {"error": f"Unable to fetch posts. {response.text}", "status": False}
            media_data = response.json()
            if not media_data.get("data"):
                return {"error": f"Unable to retrieve posts {response.text}", "status": False}
            posts_data = media_data.get("data")
            return {"message": posts_data, "status": True}
        
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

    def get(self, request, pk):
        """Retrieve a specific post"""
        post, error_response = self.get_post(pk, request.user)
        if 'comments' in request.path:
            return Response({"message": self.get_meta_comments(request.user,post.platform.platform)}, status=200)
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
    
    def get_user_access_token(self, user):
        f = Fernet(TWOFA_ENCRYPTION_KEY) 
        token=user.access_token[1:]  #do 1: to not include byte identifier
        token_decrypted=f.decrypt(token)
        token_decoded=token_decrypted.decode()
        return token_decoded
    
    def delete_facebook(self,token_decoded,post_id):
        #Get page access token
        url = f'https://graph.facebook.com/v22.0/me/accounts?access_token={token_decoded}'
        response = requests.get(url)
        if response.status_code != 200:
            # Handle error response
            return {"error": f"Unable to retrieve page access token. {response.text}", "status": False}
        metasData = response.json()
        if not metasData.get("data"):
            return {"error": "Unable to retrieve page access token 2", "status": False}
        #Get the page access token
        page_access_token = metasData.get("data")[0]["access_token"]

        url = f'https://graph.facebook.com/v22.0/{post_id}?access_token={page_access_token}'
        response=requests.delete(url)
        if response.status_code != 200:
            # Handle error response
            return {"error": f"Unable to delete post. {response.text}", "status": False}
        metasData = response.json()
        if not metasData.get("success"):
            return {"error": "Unable to retrieve post deletion status", "status": False}
        return {"message": metasData.get("success"), "status": True}

    def delete(self, request, pk):
        """Delete a post"""
        post, error_response = self.get_post(pk, request.user)

        if error_response:
            return error_response

        if post.platform.platform=='instagram':
            return Response({"message": "Instagram deletion not implemented yet"}, status=status.HTTP_400_BAD_REQUEST)
        
        delete_message = self.delete_facebook(self.get_user_access_token(request.user),post.post_id)
        if(delete_message['status'] == False):
            return Response({"message": "Some Error Deleting Post"}, status=status.HTTP_400_BAD_REQUEST)

        post.delete()
        return Response({"message": "Post deleted successfully"}, status=status.HTTP_200_OK)
