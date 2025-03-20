# backend/businesses/urls.py
from django.urls import path
from .views import BusinessDetailView

urlpatterns = [
    path("me/", BusinessDetailView.as_view(), name="business-detail"),
]