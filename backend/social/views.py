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

# Setup logger for debugging and tracking requests
logger = logging.getLogger(__name__)

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
        return Response(serialized_data, status=status.HTTP_200_OK)

class ConnectSocialAccountView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    @extend_schema(**social_connect_schema)
    def post(self, request):
        # TODO: Implement logic to generate OAuth URL for the social media provider
        return Response({"message": "OAuth initiation is not yet implemented."}, status=status.HTTP_501_NOT_IMPLEMENTED)

class OAuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    @extend_schema(**oauth_callback_schema)
    def get(self, request):
        # TODO: Implement logic to process the OAuth callback and store access token
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

