from django.urls import path
from .views import LinkedSocialAccountsView, ConnectSocialAccountView, OAuthCallbackView, DisconnectSocialAccountView

urlpatterns = [
    # Fetch linked accounts
    path("accounts/", LinkedSocialAccountsView.as_view(), name="list-social-accounts"),

    # Connect account (initiates OAuth flow)
    path("connect/<str:provider>/", ConnectSocialAccountView.as_view(), name="connect-social-account"),

    # OAuth callback (where providers redirect after authentication)
    path("callback/<str:provider>/", OAuthCallbackView.as_view(), name="oauth-callback"),

    # Disconnect account
    path("disconnect/<str:provider>/", DisconnectSocialAccountView.as_view(), name="disconnect-social-account"),
]