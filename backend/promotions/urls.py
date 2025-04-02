# promotions/urls.py
from django.urls import path
from .views import PromotionListView, PromotionDetialView

urlpatterns = [
    path("", PromotionListView.as_view(), name="promotion_list"),
    path("<int:pk>/", PromotionDetialView.as_view(), name="promotion_detail")
]
