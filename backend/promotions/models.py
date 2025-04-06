# promotions/models.py
from django.db import models
from businesses.models import Business

class PromotionCategories(models.Model):
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)

    def __str__(self):
        return self.label

    class Meta:
        verbose_name_plural = "Promotion Categories"

class Promotion(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="promotions")
    categories = models.ManyToManyField(PromotionCategories, related_name="promotions")
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    sold_count = models.PositiveIntegerField(default=0, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Promotion ({self.get_category_display()}) - {self.business.name}"

    class Meta:
        ordering = ["-created_at"]


class PromotionSuggestion(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="suggestions")
    categories = models.ManyToManyField(PromotionCategories, related_name="suggestions")
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
         return f"Promotion Suggestion - {self.business.name}"
    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Promotion Suggestions"