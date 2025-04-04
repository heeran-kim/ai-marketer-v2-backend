# promotions/models.py
from django.db import models
from businesses.models import Business

class PromotionCategories(models.Model):
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)

    def __str__(self):
        return self.label

class Promotion(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="promotions")
    categories = models.ManyToManyField(PromotionCategories, related_name="promotions")
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    sold_count = models.PositiveIntegerField(default=0, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Promotion ({self.get_category_display()}) - {self.business.name}"

    class Meta:
        ordering = ["-created_at"]