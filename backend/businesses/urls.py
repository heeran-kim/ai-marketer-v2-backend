# backend/businesses/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import BusinessDetailView, SquareViewSet

router = DefaultRouter()
router.include_root_view = False
router.register(r'square', SquareViewSet, basename='square')

urlpatterns = [
    path("me/", BusinessDetailView.as_view(), name="business-detail"),

    # Square endpoints
    path('', include(router.urls)),
]