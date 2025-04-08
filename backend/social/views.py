from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from businesses.models import Business
from .models import SocialMedia
from .serializers import SocialMediaSerializer
import logging
from drf_spectacular.utils import extend_schema
from .schemas import social_accounts_list_schema, social_disconnect_schema, social_connect_schema, oauth_callback_schema
import os
import requests

# Setup logger for debugging and tracking requests
logger = logging.getLogger(__name__)

#For Facebook API ID
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_SECRET = os.getenv("FACEBOOK_SECRET")

class LinkedSocialAccountsView(APIView):
    """
    View to retrieve all linked social accounts for the current user.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(**social_accounts_list_schema)
    def get(self, request):
        business = Business.objects.filter(owner=request.user).first()
        linked_platforms_queryset = SocialMedia.objects.filter(business=business)
        serialized_data = SocialMediaSerializer(linked_platforms_queryset, many=True).data

        #Get the access token from the user
        user=request.user
        access_token=user.access_token
        url = f'https://graph.facebook.com/v22.0/me/accounts?access_token={access_token}'
        response = requests.get(url)
        #return Response({'message':response,'access_token':access_token,'status':status.HTTP_200_OK})
        if response.status_code == 200:
            data = response.json()
            #return Response(data,status=status.HTTP_200_OK)

        return Response(serialized_data, status=status.HTTP_200_OK)

class ConnectSocialAccountView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    @extend_schema(**social_connect_schema)
    def post(self, request, provider):
        # TODO: Implement logic to generate OAuth URL for the social media provider
        
        if provider=="instagram" or provider=="facebook":
            client_id = FACEBOOK_APP_ID
            redirect_uri = f'https://localhost:3000/settings/social/{provider}'
            scope = 'email,instagram_basic,pages_show_list'
            login_url = f"https://www.facebook.com/v22.0/dialog/oauth?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code"
            return Response({'link':login_url},status=status.HTTP_200_OK)

        return Response({"message": "OAuth initiation is not yet implemented."}, status=status.HTTP_501_NOT_IMPLEMENTED)
    
class FinalizeOauthView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        # TODO: Implement logic to process the OAuth callback and store access token
        code=request.data.get('code')
        provider=request.data.get('provider')
        if(not code):
            return Response({'message': 'No Oauth Code provided!'}, status=status.HTTP_400_BAD_REQUEST)
        
        #Get Meta's access token
        app_id = FACEBOOK_APP_ID
        app_secret = FACEBOOK_SECRET
        redirect_uri = f'https://localhost:3000/settings/social/{provider}'

        url = 'https://graph.facebook.com/v22.0/oauth/access_token'
        params = {
            'client_id': app_id,
            'client_secret': app_secret,
            'redirect_uri': redirect_uri,
            'code': code,
        }

        response = requests.get(url, params=params)
        if response.status_code == 200:
            # Successful exchange, get the access token
            data = response.json()
            user=request.user
            user.access_token=data['access_token']
            user.save()

            #Retrieve the data from Meta's API
            user=request.user
            access_token=user.access_token
            url = f'https://graph.facebook.com/v22.0/me/accounts?access_token={access_token}'
            response = requests.get(url)
            #return Response({'message':response,'access_token':access_token,'status':status.HTTP_200_OK})
            if response.status_code != 200:
                # Handle error response    
                return Response({'message': 'Meta API Request Failed!'}, status=response.status_code)
            metasData = response.json()


            #For retriving the Instagram account
            instagram_account=None
            instagram_link=None
            if(provider=="instagram"):
                #get the Instagram account ID
                url = f'https://graph.facebook.com/v22.0/{metasData["data"][0]["id"]}?fields=instagram_business_account&access_token={access_token}'
                response = requests.get(url)
                data=response.json()
                if response.status_code != 200:
                    # Handle error response    
                    return Response({'message': 'Meta API Request Failed For Retrieving Instagram Account!'}, status=response.status_code)
                #get the Instagram account Name
                url = f'https://graph.facebook.com/v22.0/{data["instagram_business_account"]["id"]}?fields=username&access_token={access_token}'
                response = requests.get(url)
                data=response.json()
                if response.status_code != 200:
                    # Handle error response    
                    return Response({'message': 'Meta API Request Failed For Retrieving Instagram Account Username!'}, status=response.status_code)
                instagram_account=data["username"]
                instagram_link=f'https://www.instagram.com/{data["username"]}/'
                #return Response({'message': instagram_account}, status=status.HTTP_200_OK)
            
            # Now save the updated social media account to the database
            business = Business.objects.filter(owner=request.user).first()
            linked_platform = SocialMedia.objects.filter(business=business, platform=provider)
            if not linked_platform.exists():
                # Create a new SocialMedia instance if it doesn't exist
                social_media = SocialMedia.objects.create(
                    business=business,
                    platform=provider,
                    username=metasData['data'][0]['name'] if provider=="facebook" else instagram_account,
                    link=f'https://www.facebook.com/{metasData["data"][0]["id"]}' if provider=="facebook" else instagram_link,
                )
                social_media.save()
            else:
                # Update the existing instance
                linked_platform.first().username=metasData['data'][0]['name']
                linked_platform.first().link= f'https://www.facebook.com/{metasData["data"][0]["id"]}'
                linked_platform.first().save()

            return Response({'message': 'Successfully linked!'}, status=status.HTTP_200_OK)

        return Response({"message": "OAuth code expired or invalid for Meta API! Please reconnect via Settings!"}, status=status.HTTP_400_BAD_REQUEST)
    

class OAuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    @extend_schema(**oauth_callback_schema)
    def get(self, request,provider):
        # TODO: Implement logic to process the OAuth callback and store access token
        code=request.data.get('code')
        if(code):
            return Response({"message": code}, status=status.HTTP_200_OK)
        return Response({"message": "OAuth callback handling is not yet implemented."}, status=status.HTTP_501_NOT_IMPLEMENTED)

class DisconnectSocialAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(**social_disconnect_schema)
    def delete(self, request, provider):
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({"error": "Business not found."}, status=status.HTTP_404_NOT_FOUND)

        social_account = SocialMedia.objects.filter(business=business, platform=provider).first()
        if not social_account:
            return Response({"error": f"No connected account found for provider '{provider}'"}, status=status.HTTP_404_NOT_FOUND)

        # TODO: Revoke OAuth token before deleting from the database

        # If token revocation succeeds, delete the account from DB
        social_account.delete()
        return Response({"message": f"Disconnected from {provider} successfully"}, status=status.HTTP_200_OK)

