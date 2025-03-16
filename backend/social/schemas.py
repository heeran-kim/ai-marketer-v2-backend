from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer, OpenApiTypes, OpenApiParameter, extend_schema_field, OpenApiResponse
from rest_framework import serializers

social_accounts_list_schema = {
    'operation_id': 'List Social Accounts',
    'description': """
   Retrieve all linked social media accounts for the current authenticated user.
   
   This endpoint returns all social media platforms that the user has connected to their business profile.
   The response includes platform details, associated username, and profile link.

   **Expected Response Structure:**
   - If the user has linked accounts, the API returns an array of connected platforms.
   - If no accounts are linked, an empty list is returned (`[]`).
   
   **Related Features:**
   - Social media login integration (Feature 1.c)
   - Automated social media post publishing (Feature 3.d)
   """,
    'responses': {
        200: OpenApiResponse(
            response=inline_serializer(
                name="SocialAccountsList",
                fields={
                    "accounts": serializers.ListField(
                        child=inline_serializer(
                            name="SocialAccountDetail",
                            fields={
                                "key": serializers.CharField(help_text="Social platform key (e.g., 'facebook', 'twitter')"),
                                "label": serializers.CharField(help_text="Display name of the platform (e.g., 'Facebook', 'Twitter / X')"),
                                "username": serializers.CharField(help_text="The username or handle associated with this social account"),
                                "link": serializers.URLField(help_text="Direct URL to the user's profile on this platform")
                            }
                        )
                    )
                }
            ),
            description="List of connected social media accounts"
        ),
        401: OpenApiResponse(
            response=inline_serializer(
                name="Unauthorized",
                fields={"error": serializers.CharField(default="Authentication required")}
            ),
            description="User is not authenticated"
        )
    }
}
social_connect_schema = {
    'operation_id': 'Connect Social Account',
    'description': """
   Initiate OAuth flow to connect a new social media account.
   
   This endpoint begins the process of connecting a social media account using OAuth.
   It returns an authorization URL where the user should be redirected to authenticate
   with the social media provider.
   
   **Workflow:**
   1. Frontend calls this endpoint with the desired provider.
   2. Backend generates an OAuth authorization URL with appropriate scopes and state parameters.
   3. Frontend redirects the user to the returned authorization URL.
   4. User authenticates on the provider's website and approves permissions.
   5. Provider redirects back to the application's OAuth callback endpoint.
   6. OAuth callback endpoint exchanges the authorization code for an access token and **stores the social media account in the database**.

   **Database Changes:**
   - No changes in this step (OAuth account is stored in the callback step).

   **Implementation status:** 🟡 Partially implemented (Frontend only)

   **Related features:**
   - Social media login (Feature 1.c)
   - Social media post publishing (Feature 3.d)
   """,
    'parameters': [
        {
            'name': 'provider',
            'in': 'path',
            'required': True,
            'schema': {'type': 'string'},
            'description': "Social media provider (e.g., 'facebook', 'instagram')"
        }
    ],
    'request': inline_serializer(
        name="ConnectSocialRequest",
        fields={
            "redirectUrl": serializers.URLField(
                required=False,
                help_text="URL to redirect after authentication (optional)"
            )
        }
    ),
    'responses': {
        200: OpenApiResponse(
            response=inline_serializer(
                name="ConnectSocialResponse",
                fields={
                    "authUrl": serializers.URLField(help_text="URL to redirect user for OAuth authentication")
                }
            ),
            description="OAuth authorization URL"
        ),
        400: OpenApiResponse(
            response=inline_serializer(
                name="InvalidProvider",
                fields={"error": serializers.CharField(default="Unsupported social media provider")}
            ),
            description="Unsupported provider requested"
        ),
        401: OpenApiResponse(
            response=inline_serializer(
                name="Unauthorized",
                fields={"error": serializers.CharField(default="Authentication required")}
            ),
            description="User is not authenticated"
        )
    },
    'examples': [
        OpenApiExample(
            "Request with Redirect URL",
            value={"redirectUrl": "https://app.example.com/settings/social"},
            request_only=True,
        )
    ]
}
social_disconnect_schema = {
    'operation_id': 'Disconnect Social Account',
    'description': """
   Disconnect a linked social media account.

   This endpoint removes the connection between the user's account and the specified 
   social media platform. It **deletes the social media account record from the database**.
   
   **Current Limitations:**
   - This version **does NOT yet revoke OAuth tokens** from third-party providers.
   - The connected account is only removed from our database.

   **Workflow:**
   1. Frontend calls this endpoint with the provider name.
   2. Backend retrieves the social media account from the database.
   3. **The account record is deleted from our system.**
   4. (Future update) OAuth token revocation will be implemented.

   **Database Changes:**
   - Deletes the **SocialMedia** entry for the given provider.

   **Implementation status:** 🟡 Partially implemented (Backend + Frontend)
    - ✅ Database disconnection **Implemented**
    - ⚠️ OAuth token revocation **Not yet implemented**

   **Related features:**
   - 2.b. Businesses Management: Manage business profiles, linked accounts, and settings.
   """,
    'parameters': [
        {
            'name': 'provider',
            'in': 'path',
            'required': True,
            'schema': {'type': 'string'},
            'description': "Social media provider to disconnect (e.g., 'facebook', 'instagram')"
        }
    ],
    'responses': {
        200: OpenApiResponse(
            response=inline_serializer(
                name="DisconnectSuccess",
                fields={"message": serializers.CharField(default="Social account disconnected successfully")}
            ),
            description="Account successfully disconnected from the database"
        ),
        404: OpenApiResponse(
            response=inline_serializer(
                name="AccountNotFound",
                fields={"error": serializers.CharField(default="No connected account found for this provider")}
            ),
            description="No connected account exists for the specified provider"
        ),
        401: OpenApiResponse(
            response=inline_serializer(
                name="Unauthorized",
                fields={"error": serializers.CharField(default="Authentication required")}
            ),
            description="User is not authenticated"
        ),
    }
}
oauth_callback_schema = {
    'operation_id': 'OAuth Callback',
    'description': """
   OAuth callback endpoint for handling social media authentication redirects.
   
   This endpoint receives the OAuth callback from social media providers after a user
   has authenticated. It exchanges the authorization code for access tokens, retrieves
   the user's profile information, and **stores the connection in the database**.

   **Workflow:**
   1. The social media provider redirects the user to this endpoint with an authorization code.
   2. Backend exchanges the authorization code for an **access token**.
   3. Backend retrieves the **user's profile information** from the provider.
   4. If the account is already linked, it is **updated**. Otherwise, a **new record is created** in the database.
   5. The frontend is redirected to the specified redirect URL.

   **Database Changes:**
   - Creates or updates a **SocialMedia** entry for the authenticated user.

   **Implementation status:** 🟡 Partially implemented (Frontend only)

   **Related features:**
   - Social media login (Feature 1.c)
   - Social media post publishing (Feature 3.d)
   """,
    'parameters': [
        {
            'name': 'provider',
            'in': 'path',
            'required': True,
            'schema': {'type': 'string'},
            'description': "Social media provider (e.g., 'facebook', 'instagram')"
        },
        {
            'name': 'code',
            'in': 'query',
            'required': True,
            'schema': {'type': 'string'},
            'description': "Authorization code from OAuth provider"
        },
        {
            'name': 'state',
            'in': 'query',
            'required': True,
            'schema': {'type': 'string'},
            'description': "State parameter to prevent CSRF attacks"
        }
    ],
    'responses': {
        302: OpenApiResponse(
            description="Redirect to frontend application with success/error status"
        ),
        400: OpenApiResponse(
            response=inline_serializer(
                name="InvalidCallback",
                fields={"error": serializers.CharField(default="Invalid callback parameters")}
            ),
            description="Invalid OAuth callback parameters"
        )
    }
}