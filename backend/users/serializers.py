from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

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

class TraditionalLoginSerializer(serializers.Serializer):
    """Traditional login with email & password"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        """Authenticate user and generate tokens"""
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError({"error": "Incorrect email or password."})

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }

class SocialLoginSerializer(serializers.Serializer):
    """Social login via OAuth2"""
    provider = serializers.CharField()
    access_token = serializers.CharField()

    def validate(self, data):
        # TODO
        pass

class PasskeyLoginSerializer(serializers.Serializer):
    """Passkey authentication"""
    passkey_data = serializers.CharField()

    def validate(self, data):
        # TODO
        pass

class TwoFactorVerificationSerializer(serializers.Serializer):
    """Two-factor authentication (2FA)"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    otp = serializers.CharField()

    def validate(self, data):
        # TODO
        pass

class ForgotPasswordSerializer(serializers.Serializer):
    """
    Serializer for handling password reset requests.

    Functionality:
    - Validates if the provided email exists in the system.
    - Generates a password reset token.
    - Sends an email with the reset link.
    """
    email = serializers.EmailField()

    def validate(self, data):
        """Checks if the provided email exists in the database."""
        # TODO: Check if the email is registered
        pass

    def save(self, **kwargs):
        """Generates a password reset token and sends an email."""
        # TODO: Generate password reset token
        # TODO: Send email with reset link
        pass

class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for resetting user password.

    Functionality:
    - Validates the provided reset token.
    - Updates the user's password if the token is valid.
    - Ensures the new password meets security requirements.
    """
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        """Validates the reset token and checks password strength."""
        # TODO: Validate token (check if it exists and is not expired)
        # TODO: Ensure new password meets security policies
        pass

    def save(self, **kwargs):
        """Updates the user's password."""
        # TODO: Reset user password
        pass