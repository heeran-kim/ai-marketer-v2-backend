from django.urls import path
from .views import show, create

urlpatterns = [
    path("", show, name="show"),
    path("new/", create, name="create"),
]
