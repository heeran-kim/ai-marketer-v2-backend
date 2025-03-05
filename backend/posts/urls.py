from django.urls import path
from .views import PostListView, PostCreateView

urlpatterns = [
    path("", PostListView.as_view(), name="post-list"),             # GET /api/posts/
    path("create/", PostCreateView.as_view(), name="post-create"),  # GET/POST /api/posts/create/
]