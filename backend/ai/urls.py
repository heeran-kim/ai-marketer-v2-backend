from django.urls import path
from .views import analyse_image, generate_caption

urlpatterns = [
    path("images/analyse/", analyse_image, name="analyse-image"),
    path("captions/generate/", generate_caption, name="generate-caption"),
]
