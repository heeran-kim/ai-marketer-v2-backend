# users/schemas.py
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer, OpenApiTypes, OpenApiParameter, extend_schema_field, OpenApiResponse
from rest_framework import serializers

# Register schema
register_schema = {
    'operation_id': 'Register',
    'description': """
    Create a new user account with email, name, and password.
    
    This endpoint allows users to create an account securely.
    The registration process validates email format and password security.
    Once registered, the user can log in using their credentials.
    
    Implementation status: ✅ Fully implemented (Frontend & Backend) – Feature 1.a
    
    Future enhancements:
    - Will be extended to support social registration - Feature 1.c
    - Will support passkey registration for biometric authentication - Feature 1.d
    """,
    'request': {
        "application/json": inline_serializer(
            name='RegisterRequest',
            fields={
                'name': serializers.CharField(required=True, help_text="User's full name"),
                'email': serializers.EmailField(required=True, help_text="User's email address (used for login)"),
                'password': serializers.CharField(required=True, min_length=6, help_text="Password (min 6 characters)"),
                'role': serializers.ChoiceField(
                    choices=["admin", "business_owner"],
                    default="business_owner",
                    help_text="User role (defaults to business_owner)"
                )
            }
        )
    },
    'responses': {
        201: inline_serializer(
            name='RegistrationSuccess',
            fields={
                'message': serializers.CharField(default="User created successfully")
            }
        ),
        400: inline_serializer(
            name='ValidationError',
            fields={
                'email': serializers.ListField(child=serializers.CharField(), required=False, default=["Invalid email format."]),
                'name': serializers.ListField(child=serializers.CharField(), required=False, default=["Name is required."]),
                'password': serializers.ListField(child=serializers.CharField(), required=False, default=["Password must be at least 6 characters."]),
                'role': serializers.ListField(child=serializers.CharField(), required=False, default=["Invalid role."]),
            }
        )
    },
    'examples': [
        OpenApiExample(
            'Valid Registration',
            value={'name': 'John Doe', 'email': 'john@example.com', 'password': 'secure123', 'role': 'business_owner'},
            request_only=True,
        )
    ]
}

# Login schema
login_schema = {
    'operation_id': 'Login',
    'description':  """
    Authenticate a user and receive tokens.
    
    This endpoint allows users to log in using an authentication method that securely verifies credentials.
    It returns a refresh token in the response body and sets an access token in an HTTP-only secure cookie for enhanced security.
    
    **Implementation Status**: ✅ Fully implemented (Frontend & Backend) – Feature 1.a

    **Future Enhancements**:
    - Support for social login via OAuth2 (Google, Facebook, Apple) – Feature 1.c
    - Integration of passkey/biometric authentication – Feature 1.d
    - Implementation of two-factor authentication (2FA) – Feature 1.e
    """,
    'responses': {
        200: OpenApiResponse(
            response=inline_serializer(
                name="LoginSuccess",
                fields={
                    "message": serializers.CharField(default="Login successful"),
                    "refresh": serializers.CharField(),
                }
            ),
            description="Successful login. Access token is set in HttpOnly Cookie."
        ),
        400: OpenApiResponse(
            response=inline_serializer(
                name="ValidationError",
                fields={"error": serializers.CharField(default="Incorrect email or password.")},
            ),
            description="Validation error. Incorrect email or password."
        ),
        401: OpenApiResponse(
            response=inline_serializer(
                name="UnauthorizedError",
                fields={"error": serializers.CharField(default="Invalid or expired token.")},
            ),
            description="Unauthorized request. Token is missing or invalid."
        ),
        403: OpenApiResponse(
            response=inline_serializer(
                name="ForbiddenError",
                fields={"error": serializers.CharField(default="Account is disabled or restricted.")},
            ),
            description="User account is disabled or restricted."
        ),
    },
    "examples": [
        OpenApiExample(
            "Traditional Login",
            value={"method": "traditional", "credentials": {"email": "user@example.com", "password": "secure123"}},
            request_only=True,
        ),
        OpenApiExample(
            "Social Login",
            value={"method": "social", "credentials": {"provider": "google", "access_token": "some_token"}},
            request_only=True,
        ),
        OpenApiExample(
            "Passkey Login",
            value={"method": "passkey", "credentials": {"passkey_data": "some_passkey_data"}},
            request_only=True,
        ),
        OpenApiExample(
            "2FA Login",
            value={"method": "2fa", "credentials": {"email": "user@example.com", "password": "secure123", "otp": "123456"}},
            request_only=True,
        ),
    ],
}

# Me schema
me_schema = {
    'operation_id': 'Me',
    'description': """
    Retrieve the current authenticated user's profile.

    This endpoint returns the profile information of the currently authenticated user, including their email, name, and role.
    It requires a valid access token provided via an HTTP-only cookie.

    Implementation status: ✅ Fully implemented (Frontend & Backend) – Feature 1.a
    """,
    'responses': {
        200: inline_serializer(
            name="UserProfile",
            fields={
                "email": serializers.EmailField(),
                "name": serializers.CharField(),
                "role": serializers.ChoiceField(choices=["admin", "business_owner"]),
            },
            default={
                "email": "user@example.com",
                "name": "John Doe",
                "role": "business_owner"
            }
        ),
        401: OpenApiResponse(
            response=inline_serializer(
                name="UnauthorizedResponse",
                fields={
                    "detail": serializers.CharField()
                }
            ),
            description="Unauthorized - Missing or invalid authentication credentials.",
            examples=[
                OpenApiExample(
                    name="Missing Token",
                    summary="No authentication token provided",
                    value={"detail": "Authentication credentials were not provided."}
                ),
                OpenApiExample(
                    name="Invalid Token",
                    summary="Invalid authentication token",
                    value={"detail": "Invalid token."}
                )
            ]
        )
    }
}

# Logout schema
logout_schema = {
    'operation_id': 'Logout',
    'description': """
    Log out the current user.
    
    This endpoint invalidates the user's authentication by:
    1. Clearing the access token cookie
    2. Blacklisting the refresh token to prevent reuse
    3. Ending the current session
    
    Implementation status: ✅ Fully implemented (Frontend & Backend) – Feature 1.a
    """,
    'responses': {
        200: inline_serializer(
            name="LogoutSuccess",
            fields={"message": serializers.CharField(default="Logged out successfully")}
        )
    }
}

# Forgot Password schema
forgot_password_schema = {
    'operation_id': 'Forgot Password',
    'description':"""
    Handles password reset email requests.

    This endpoint allows users to request a password reset by providing their registered email.
    If the email exists in the system, a password reset token is generated and sent via email.

    Workflow:
    1. The user submits their email address.
    2. If the email is registered, the system generates a password reset token.
    3. An email with the reset link is sent to the user.
    4. If the email does not exist, the system still returns a success message (to prevent email enumeration attacks).
    
    Where to Modify:
    - Modify password reset request logic: `ForgotPasswordSerializer`
    - Adjust token expiration time: `PASSWORD_RESET_EXPIRATION_HOURS` (settings.py)
    - Customize email content: `send_password_reset_email()` (utils.py)
    """,
    'request': {
        "application/json": inline_serializer(
            name="ForgotPasswordRequest",
            fields={
                "email": serializers.EmailField(help_text="User's registered email")
            }
        )
    },
    'responses': {
        200: OpenApiResponse(
            response=inline_serializer(
                name="ForgotPasswordSuccess",
                fields={"message": serializers.CharField(default="Password reset email sent")}
            ),
            description="Success: Password reset email sent."
        ),
        400: OpenApiResponse(
            response=inline_serializer(
                name="ValidationError",
                fields={"error": serializers.CharField(default="Invalid email format")}
            ),
            description="Invalid request. Check email format."
        ),
    },
    'examples': [
        OpenApiExample(
            "Valid Request",
            value={"email": "user@example.com"},
            request_only=True,
        ),
        OpenApiExample(
            "Invalid Email Format",
            value={"email": "invalid-email"},
            request_only=True,
        ),
    ]
}

# Reset Password schema
reset_password_schema = {
    'operation_id': 'Reset Password',
    'description': """
    Handles password reset requests using a reset token.

    This endpoint allows users to reset their password by providing a valid reset token and a new password.

    Workflow:
    1. The user clicks the password reset link from their email, which contains a unique token.
    2. The frontend collects the token and the new password, then sends a POST request to this endpoint.
    3. The backend validates the token, ensures it hasn't expired, and resets the user's password.
    4. If successful, the response confirms that the password has been reset.

    Where to Modify:
    - Modify password reset logic: `ResetPasswordSerializer`
    - Adjust token expiration time: `PASSWORD_RESET_EXPIRATION_HOURS` (settings.py)
    """,
    'request': {
        "application/json": inline_serializer(
            name="ResetPasswordRequest",
            fields={
                "token": serializers.CharField(help_text="Password reset token received via email"),
                "new_password": serializers.CharField(write_only=True, help_text="New password (min 6 characters)", min_length=6),
            }
        )
    },
    'responses': {
        200: OpenApiResponse(
            response=inline_serializer(
                name="ResetPasswordSuccess",
                fields={"message": serializers.CharField(default="Password has been reset")}
            ),
            description="Success: Password has been reset."
        ),
        400: OpenApiResponse(
            response=inline_serializer(
                name="InvalidToken",
                fields={"error": serializers.CharField(default="Invalid or expired token.")}
            ),
            description="Invalid or expired reset token."
        ),
        400: OpenApiResponse(
            response=inline_serializer(
                name="WeakPassword",
                fields={"error": serializers.CharField(default="Password does not meet security requirements.")}
            ),
            description="Password does not meet security requirements."
        ),
    },
    'examples': [
        OpenApiExample(
            "Valid Reset Request",
            value={"token": "some_valid_token", "new_password": "SecurePass123"},
            request_only=True,
        ),
        OpenApiExample(
            "Invalid Token",
            value={"token": "invalid_token", "new_password": "SecurePass123"},
            request_only=True,
        ),
        OpenApiExample(
            "Weak Password",
            value={"token": "some_valid_token", "new_password": "123"},
            request_only=True,
        ),
    ]
}