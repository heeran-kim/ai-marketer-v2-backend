# backend/sales/models.py
from django.db import models
from businesses.models import Business

def sales_file_path(instance, filename):
    return f'business_sales/{instance.business.id}/{filename}'

class SalesData(models.Model):
    """Model representing an uploaded sales data file"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="sales_data")
    file = models.FileField(upload_to=sales_file_path)
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.filename} - {self.business.name}"

class SalesDataPoint(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    date = models.DateField()
    revenue = models.DecimalField(max_digits=10, decimal_places=2)
    source_file = models.ForeignKey(SalesData, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['business', 'date']