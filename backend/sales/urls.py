# backend/sales/urls.py
from django.urls import path
from .views import SalesDataView

urlpatterns = [
    path('', SalesDataView.as_view(), name='sales-data'),
]
