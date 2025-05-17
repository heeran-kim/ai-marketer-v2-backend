# backend/sales/urls.py
from django.urls import path

from .views import SalesDataView, RefreshSalesDataView

urlpatterns = [
    path('', SalesDataView.as_view(), name='sales-data'),
    path('refresh/', RefreshSalesDataView.as_view(), name='sales-refresh')
]
