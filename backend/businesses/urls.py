from django.urls import path
from .views import get_dashboard_data, get_business_data

urlpatterns = [
    path("dashboard/", get_dashboard_data, name="dashboard-data"),
    path("businesses/me/", get_business_data, name="business-data"),
]
