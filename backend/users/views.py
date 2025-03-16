from rest_framework.parsers import JSONParser
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, TraditionalLoginSerializer, SocialLoginSerializer, PasskeyLoginSerializer, TwoFactorVerificationSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from users.authentication import CustomJWTAuthentication
from django.conf import settings
import logging
from drf_spectacular.utils import extend_schema
from .schemas import register_schema, login_schema, me_schema, logout_schema, forgot_password_schema, reset_password_schema

# Get the custom User model
User = get_user_model()

# Setup logger for debugging and tracking requests
logger = logging.getLogger(__name__)


@extend_schema(**register_schema)
class RegisterView(generics.CreateAPIView):
    """
    API for user registration
    """
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        """
        Handles user registration.
        """
        response = super().create(request, *args, **kwargs)
        response.data = {"message": "User created successfully"}
        return response


class LoginView(APIView):
    """
    API for user authentication.
    - Returns access & refresh tokens if authentication is successful
    - Stores the access token in HttpOnly Secure Cookie
    """
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def get_serializer_class(self):
        """Returns the appropriate serializer based on the login method"""
        strategy_map = {
            "traditional": TraditionalLoginSerializer,
            "social": SocialLoginSerializer,
            "passkey": PasskeyLoginSerializer,
            "2fa": TwoFactorVerificationSerializer,
        }
        return strategy_map.get(self.request.data.get('method', 'traditional'))

    @extend_schema(**login_schema)
    def post(self, request):
        """Handles user login requests dynamically"""
        serializer_class = self.get_serializer_class()
        if not serializer_class:
            return Response(
                {"error": f"Unsupported login method: {request.data.method}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = serializer_class(data=request.data.get("credentials", {}))
        serializer.is_valid(raise_exception=True)
        tokens = serializer.validated_data

        response = Response({
            "message": "Login successful",
            "refresh": tokens["refresh"], # Return refresh token in response
        }, status=status.HTTP_200_OK)

        # Set JWT access token in HttpOnly Secure Cookie
        response.set_cookie(
            key=settings.SIMPLE_JWT["AUTH_COOKIE"],  # Cookie Name
            value=tokens["access"],  # Save access token
            httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],  # Secure Cookie
            secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],  # HTTPS-only
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],  # Cross-site protection
            max_age=60 * 60 * 24,  # Valid for 1 day
        )
        # Return the refresh token in the response (frontend can store it securely)
        return response

class UserProfileView(APIView):
    """
    API to get the currently authenticated user's information.
    Requires the user to be logged in (JWT authentication).
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(**me_schema)
    def get(self, request):
        """
        Retrieves user profile details from the authenticated request.
        """
        user = request.user
        return Response({
            "email": user.email,
            "name": user.name,
            "role": user.role
        })

class LogoutView(APIView):
    """
    API for user logout.
    - Invalidates the refresh token
    - Deletes the access token from HttpOnly Cookie
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(**logout_schema)
    def post(self, request):
        """
        Handles user logout by blacklisting the refresh token.
        - Also removes JWT access token from HttpOnly Cookie.
        """
        response = Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

        # Delete JWT access token from cookies
        response.set_cookie(
            key=settings.SIMPLE_JWT["AUTH_COOKIE"],
            value="",
            httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
            secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            expires="Thu, 01 Jan 1970 00:00:00 GMT",
            max_age=0,
        )

        # Remove Refresh Token from HttpOnly Cookie
        response.delete_cookie("refresh_token")

        # Blacklist the refresh token (optional, only if using blacklisting)
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception as e:
                logger.error(f"❌ Failed to blacklist refresh token: {e}")

        return response


class ForgotPasswordView(GenericAPIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    serializer_class = ForgotPasswordSerializer

    @extend_schema(**forgot_password_schema)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)


class ResetPasswordView(GenericAPIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    serializer_class = ResetPasswordSerializer

    @extend_schema(**reset_password_schema)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password has been reset"}, status=status.HTTP_200_OK)

