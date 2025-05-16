from django.db.models.signals import post_migrate
from django.dispatch import receiver

from config.constants import PROMOTION_CATEGORIES_OPTIONS
from promotions.models import PromotionCategories

@receiver(post_migrate)
def populate_promotion_categories(sender, **kwargs):
    if sender.name == "promotions":
        for option in PROMOTION_CATEGORIES_OPTIONS:
            PromotionCategories.objects.get_or_create(key=option["key"], label=option["label"])