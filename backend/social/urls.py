from django.urls import path

from .views import (
    ConnectSocialAccountView,
    DisconnectSocialAccountView,
    FinalizeOauthView,
    LinkedSocialAccountsView,
    OAuthCallbackView,
)

urlpatterns = [
    # Fetch linked accounts
    path("accounts/", LinkedSocialAccountsView.as_view(), name="list-social-accounts"),

    # Get access token from oauth code
    path("finalize_oauth/", FinalizeOauthView.as_view(), name="finalize_oauth"),

    # Connect account (initiates OAuth flow)
    path("connect/<str:provider>/", ConnectSocialAccountView.as_view(), name="connect-social-account"),

    # OAuth callback (where providers redirect after authentication)
    path("callback/<str:provider>/", OAuthCallbackView.as_view(), name="oauth-callback"),

    # Disconnect account
    path("disconnect/<str:provider>/", DisconnectSocialAccountView.as_view(), name="disconnect-social-account"),
]