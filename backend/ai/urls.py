from django.urls import path
from .views import analyse_image

urlpatterns = [
    path("images/analyse/", analyse_image, name="analyse-image"),
]
