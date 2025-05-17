# backend/users/views.py
import base64
from io import BytesIO
import logging

from cryptography.fernet import Fernet
from django.conf import settings
from django.http import JsonResponse
import pyotp
import qrcode
from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from businesses.models import Business
from .serializers import (
    ForgotPasswordSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    TraditionalLoginSerializer,
    TwoFactorVerificationSerializer,
)

TWOFA_ENCRYPTION_KEY = settings.TWOFA_ENCRYPTION_KEY

logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    """API endpoint for registering a new user."""
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        """Creates a new user and returns a success message."""
        response = super().create(request, *args, **kwargs)
        response.data = {"message": "User created successfully"}
        return response


class LoginView(APIView):
    """
    Handles user authentication.
    Stores the access token in an HttpOnly Secure Cookie.
    """
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def get_serializer_class(self):
        """Returns the appropriate serializer based on the login method"""
        strategy_map = {
            "traditional": TraditionalLoginSerializer,
            "2fa": TwoFactorVerificationSerializer,
        }
        return strategy_map.get(self.request.data.get('method', 'traditional'))

    def post(self, request):
        """Processes login and sets JWT access token cookie."""
        serializer_class = self.get_serializer_class()
        if not serializer_class:
            return Response(
                {"error": f"Unsupported login method: {request.data.method}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = serializer_class(data=request.data.get("credentials", {}))
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        token = AccessToken.for_user(user)

        response = Response({
            "message": "Login successful",
        }, status=status.HTTP_200_OK)

        # Set JWT access token in HttpOnly Secure Cookie
        response.set_cookie(
            key=settings.SIMPLE_JWT["AUTH_COOKIE"],
            value=str(token),
            path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
            secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"], 
            max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        )

        return response

class UserProfileView(APIView):
    """
    API to get the currently authenticated user's information.
    Requires the user to be logged in (JWT authentication).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Retrieves user profile details from the authenticated request.
        """
        user = request.user
        business = Business.objects.filter(owner=user).first()
        return Response({
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "business_id": business.id if business else None,
        })

class LogoutView(APIView):
    """
    API for user logout.
    - Deletes the access token from HttpOnly Cookie
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles user logout by removing JWT access token from HttpOnly Cookie.
        """
        response = Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

        # Delete JWT access token from cookies
        response.delete_cookie(
            settings.SIMPLE_JWT["AUTH_COOKIE"],
            path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
        )

        return response

class DeleteAccountView(APIView):
    """
    API for deleting a user account.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """
        Deletes the authenticated user's account.
        """
        user = request.user
        user.delete()
        response = Response({"message": "Account deleted successfully"}, status=status.HTTP_200_OK)
        response.delete_cookie(
            settings.SIMPLE_JWT["AUTH_COOKIE"],
            path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
        )
        return response

class ForgotPasswordView(GenericAPIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)

class ResetPasswordView(GenericAPIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password has been reset"}, status=status.HTTP_200_OK)

class Check2FA(APIView):
    # permission_classes = [AllowAny]
    # parser_classes = [JSONParser]
    # serializer_class = TWOFASerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code=request.data.get('code')

        user=request.user
        #if code is given then user is trying to add 2fa
        if(code!=''):
            #try check if the code is valid      
            f = Fernet(TWOFA_ENCRYPTION_KEY) 
            otp_code = code
            secret=user.secret_2fa[1:]  #do 1: to not include byte identifier
            secret_decrypted=f.decrypt(secret)
            secret_decoded=secret_decrypted.decode()
            totp = pyotp.TOTP(secret_decoded)

            if not totp.verify(otp_code):
                return Response({'status': False}, status=status.HTTP_400_BAD_REQUEST)

            user.requires_2fa = True
            user.save()
            return Response({"status": user.requires_2fa}, status=status.HTTP_200_OK)
        #else user is just checking if it is enabled

        return Response({"status": user.requires_2fa}, status=status.HTTP_200_OK)
    
class Remove2FA(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user=request.user
        user.secret_2fa = ""
        user.requires_2fa = False
        user.save()
        return Response({"status": user.requires_2fa}, status=status.HTTP_200_OK)
    
class Enable2FA(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        user=request.user

        secret = pyotp.random_base32()
        secret_bytes = str.encode(secret) #convert to bytes
        f = Fernet(TWOFA_ENCRYPTION_KEY) #assign encryption key
        # the plaintext is converted to ciphertext 
        secret_encrypted = f.encrypt(secret_bytes) 
        

        user.secret_2fa = secret_encrypted
        user.save()
        #generate qr code
        otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(user.email, issuer_name="AI-Marketer")
        qr = qrcode.make(otp_uri)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()  #convert image to Base64

        return JsonResponse({"qr_code": f"data:image/png;base64,{qr_base64}"})

