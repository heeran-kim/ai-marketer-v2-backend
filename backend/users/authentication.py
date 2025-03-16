from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        logger.info(f"🛠 Checking request.COOKIES: {request.COOKIES}")

        token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])
        if token is None:
            logger.warning("❌ No access_token found in cookies")
            return None  # 인증 실패

        try:
            validated_token = self.get_validated_token(token)
            user = self.get_user(validated_token)
            logger.info(f"✅ Authentication successful for user: {user}")
            return user, validated_token
        except Exception as e:
            logger.error(f"❌ JWT Authentication failed: {e}")
            return None  # 인증 실패