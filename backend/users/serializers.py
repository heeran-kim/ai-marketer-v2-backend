from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

# TEST
# docker exec -it promoease-backend-backend-1 python test_serializers.py

User = get_user_model() # AUTH_USER_MODEL = 'users.User'

class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        """Create a new user with encrypted password"""
        return User.objects.create_user(**validated_data)

class LoginSerializer(serializers.Serializer):
    """Serializer for user authentication"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Authenticate user and generate tokens"""
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError({"detail": "Incorrect email or password."})

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {"email": user.email, "role": user.role}
        }