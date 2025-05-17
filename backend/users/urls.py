# backend/users/urls.py
from django.urls import path

from .views import (
    Check2FA,
    DeleteAccountView,
    Enable2FA,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    RegisterView,
    Remove2FA,
    ResetPasswordView,
    UserProfileView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('delete/', DeleteAccountView.as_view(), name='delete'),
    path('password/forgot/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('password/reset/', ResetPasswordView.as_view(), name='reset-password'),
    
    #2fa endpoints
    path('2fa-check/',Check2FA.as_view(),name='check2fa'),
    path('2fa-remove/',Remove2FA.as_view(),name='remove2fa'),
    path('2fa-qr/',Enable2FA.as_view(),name='qr2fa'),
]