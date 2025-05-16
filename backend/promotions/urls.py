# promotions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PromotionViewSet

# Set up a router to automatically generate URL patterns for the PromotionViewSet
# This includes list, create, retrieve, update, and delete operations
router = DefaultRouter()
router.include_root_view = False
router.register(r'', PromotionViewSet, basename='promotion')

# Include the router-generated URLs in the urlpatterns
# This will cover endpoints like:
# - GET /           -> list promotions
# - GET /?type=suggestions -> list suggestions
# - POST /          -> create promotion
# - GET /{id}/      -> retrieve promotion
# - PUT /{id}/      -> update promotion
# - DELETE /{id}/   -> delete promotion
# - GENERATE        -> generate promotion suggestions
urlpatterns = [
    path('', include(router.urls)),
]
