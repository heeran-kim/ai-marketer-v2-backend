from django.db.models.signals import post_migrate
from django.dispatch import receiver

from config.constants import POST_CATEGORIES_OPTIONS
from posts.models import Category

@receiver(post_migrate)
def populate_categories(sender, **kwargs):
    """
    Signal handler to populate post categories after migration.
    Creates category entries from the options defined in constants.
    """
    if sender.name == "posts":
        for option in POST_CATEGORIES_OPTIONS:
            Category.objects.get_or_create(key=option["key"], label=option["label"])
