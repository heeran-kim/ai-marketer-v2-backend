# backend/users/serializers.py
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
import pyotp
from rest_framework import serializers

User = get_user_model()

TWOFA_ENCRYPTION_KEY = settings.TWOFA_ENCRYPTION_KEY

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
        email = data.get('email')
        try:
            # Get the user with this email
            user = User.objects.get(email=email)
            # Store user in the validated data for later use
            data['user'] = user
            return data
        except User.DoesNotExist:
            raise serializers.ValidationError("No user is registered with this email address.")

    def save(self, **kwargs):
        """Generates a password reset token and sends an email."""
        user = self.validated_data['user']
        
        # Generate token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        # Create reset link for frontend
        frontend_url = settings.FRONTEND_BASE_URL
        reset_link = f"{frontend_url}/reset-password?uid={uid}&token={token}"
        
        # Compose email content
        subject = "Reset your AI Marketer password"
        
        # Plain text email content
        message = f"""
Hello {user.name if hasattr(user, 'name') else ''},

You're receiving this email because you requested a password reset for your AI Marketer account.

Please click the link below to set a new password:
{reset_link}

This link will expire in 24 hours for security reasons.

If you didn't request this password reset, please ignore this email.

Thanks,
The AI Marketer Team
        """
        
        # Send email (plain text only)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )
        
        return user

class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for resetting user password.

    Functionality:
    - Validates the provided reset token.
    - Updates the user's password if the token is valid.
    - Ensures the new password meets security requirements.
    """
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        """Validates the reset token and checks password strength."""
        try:
            # Decode the UID
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid user identifier")
        
        # Validate token
        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError("Invalid or expired token")
        
        # Validate password strength
        try:
            validate_password(data['new_password'], user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        
        # Store user for save method
        data['user'] = user
        return data

    def save(self, **kwargs):
        """Updates the user's password."""
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return user
