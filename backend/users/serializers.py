from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate

import pyotp
import qrcode
import os

from cryptography.fernet import Fernet #cryptography package

User = get_user_model() # AUTH_USER_MODEL = 'users.User'


TWOFA_ENCRYPTION_KEY = os.getenv("TWOFA_ENCRYPTION_KEY")


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for traditional user registration with email & password.
    This handles creating a new user with encrypted password storage.
    """
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        """Create a new user with encrypted password"""
        return User.objects.create_user(**validated_data)

class TraditionalLoginSerializer(serializers.Serializer):
    """
    Serializer for traditional login using email & password.

    - Validates user credentials and returns the authenticated user.
    - If the user has two-factor authentication (2FA) enabled, authentication will not be completed immediately.
      Instead, the system will indicate that a second factor (OTP) is required.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        """
        Authenticate user and return the validated user instance.
        If 2FA is enabled, raise a validation error indicating further verification is required.
        """
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError({"error": "Incorrect email or password."})

        # TODO: If user has 2FA enabled, return a response indicating that OTP is required.

        if (user.requires_2fa):
            raise serializers.ValidationError({"error": "Requires 2FA Code."})


        return user # Return the authenticated user

class SocialLoginSerializer(serializers.Serializer):
    """
    Serializer for social login via OAuth2 providers (Google, Facebook, etc.).
    This handles authentication using third-party access tokens.
    """
    provider = serializers.CharField() # Example: "google", "facebook"
    access_token = serializers.CharField()

    def validate(self, data):
        """
        Validate the provided access token with the respective OAuth provider.

        - If the token is valid, retrieve the user associated with it.
        - If no existing user is found, create a new one.
        - Return the authenticated user.
        """
        # TODO: Implement provider-specific OAuth validation and user creation logic
        pass

class PasskeyLoginSerializer(serializers.Serializer):
    """
    Serializer for passkey authentication (WebAuthn/FIDO2).
    This allows users to authenticate using biometric or security keys.
    """
    passkey_data = serializers.CharField()

    def validate(self, data):
        """
        Validate passkey authentication.

        - If the email exists, authenticate user with stored passkey.
        - If the email does not exist, create a new user and store the passkey.
        - Return the authenticated user.
        """
        # TODO: Implement WebAuthn passkey registration logic
        pass

class TwoFactorVerificationSerializer(serializers.Serializer):
    """
    Serializer for two-factor authentication (2FA) verification.

    - This is the second step of the authentication process.
    - Used when a user logs in using traditional login, but 2FA is enabled.
    - Requires email, password, and OTP (One-Time Password).
    - Authenticates the user first with email & password.
    - Then verifies the provided OTP.
    - If successful, returns the authenticated user.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    code = serializers.CharField()

    def validate(self, data):
        """
        Validate user credentials and OTP.

        - First, authenticate the user using email & password.
        - If authentication is successful, check if the OTP is valid.
        - If both checks pass, return the authenticated user.
        """
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError({"error": "Incorrect email or password."})

        # TODO: If user has 2FA enabled, return a response indicating that OTP is required.

        if (user.requires_2fa==False):
            raise serializers.ValidationError({"error": "User doesn't require 2FA!"})

        #raise serializers.ValidationError({"error": data.keys()})

        if not (user.secret_2fa):
            raise serializers.ValidationError({"error": "User doesn't require 2FA!"})
        
        f = Fernet(TWOFA_ENCRYPTION_KEY) 
        otp_code = data['code']
        secret=user.secret_2fa[1:]  #do 1: to not include byte identifier
        secret_decrypted=f.decrypt(secret)
        secret_decoded=secret_decrypted.decode()
        totp = pyotp.TOTP(secret_decoded)

        if totp.verify(otp_code):
            return user # Return the authenticated user
        else:
            raise serializers.ValidationError({"error": "Wrong Authentication Code!"})
        

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
    

