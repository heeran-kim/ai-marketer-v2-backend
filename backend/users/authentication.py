import logging

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])
        if token is None:
            logger.warning("❌ No access_token found in cookies")
            return None

        try:
            validated_token = self.get_validated_token(token)
            user = self.get_user(validated_token)
            return user, validated_token

        except Exception as e:
            logger.error(f"❌ JWT Authentication failed: {e}")
            return None