from django.urls import path
from .views import PostListCreateView, PostDeleteView

urlpatterns = [
    path("", PostListCreateView.as_view(), name="post_list_create"), # GET,CREATE /api/posts/
    path("<int:pk>/delete/", PostDeleteView.as_view(), name="post_delete"), # DELETE /api/posts/{id}/delete
]