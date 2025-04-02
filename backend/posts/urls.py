# posts/urls.py
from django.urls import path
from .views import PostListCreateView, PostDetailView

urlpatterns = [
    path("", PostListCreateView.as_view(), name="post_list_create"), # GET,CREATE /api/posts/
    path("<int:pk>/", PostDetailView.as_view(), name="post_detail"), # GET,PATCH,DELETE /api/posts/{id}/
]
