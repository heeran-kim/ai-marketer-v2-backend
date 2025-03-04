from django.db.models.signals import post_migrate
from django.dispatch import receiver
from posts.models import Category
from config.constants import POST_CATEGORIES_OPTIONS

@receiver(post_migrate)
def populate_categories(sender, **kwargs):
    if sender.name == "posts":
        for option in POST_CATEGORIES_OPTIONS:
            Category.objects.get_or_create(key=option["key"], label=option["label"])
