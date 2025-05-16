from django.urls import path
from .views import RegisterView, LoginView, UserProfileView, LogoutView, ForgotPasswordView, ResetPasswordView,Check2FA,Remove2FA,Enable2FA,DeleteAccountView
    
from businesses.views import GooglePlaceLookupView  # import the view

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password/forgot/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('password/reset/', ResetPasswordView.as_view(), name='reset-password'),
    
    #2fa endpoints
    path('2fa-check/',Check2FA.as_view(),name='check2fa'),
    path('2fa-remove/',Remove2FA.as_view(),name='remove2fa'),
    path('2fa-qr/',Enable2FA.as_view(),name='qr2fa'),

    # New endpoints
    
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),

    path('place-lookup/', GooglePlaceLookupView.as_view(), name='place-lookup')

]