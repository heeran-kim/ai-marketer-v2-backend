from django.urls import path
from .views import generate_caption

urlpatterns = [
    path("captions/generate/", generate_caption, name="generate-caption"),
]
