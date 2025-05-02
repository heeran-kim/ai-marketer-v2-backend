# posts/urls.py
from django.urls import path
from .views import PostListCreateView, PostDetailView

urlpatterns = [
    path("", PostListCreateView.as_view(), name="post_list_create"), # LIST, CREATE GET,POST /api/posts/
    path("<int:pk>/", PostDetailView.as_view(), name="post_detail"), # GET,PATCH,DELETE /api/posts/{id}/
    path("<int:pk>/comments/", PostDetailView.as_view(), name="post_comments"), # GET /api/posts/{id}/comments
]
