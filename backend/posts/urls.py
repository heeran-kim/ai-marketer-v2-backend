from django.urls import path
from .views import PostListView, PostCreateView, PostDeleteView

urlpatterns = [
    path("", PostListView.as_view(), name="post_list"),             # GET /api/posts/
    path("create/", PostCreateView.as_view(), name="post_create"),  # GET/POST /api/posts/create/
    path("<int:pk>/delete/", PostDeleteView.as_view(), name="post_delete"), # DELETE /api/posts/{id}/delete
]