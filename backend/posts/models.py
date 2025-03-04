from django.db import models
from businesses.models import Business
from social.models import SocialMedia
from config.constants import POST_CATEGORIES_OPTIONS, POST_STATUS_OPTIONS

class Category(models.Model):
    key = models.CharField(max_length=50, unique=True)  # Category key (e.g., 'brand_story')
    label = models.CharField(max_length=100)  # Display name for the category (e.g., 'Brand Story')

    def __str__(self):
        return self.label

class Post(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="posts")
    platform = models.ForeignKey(SocialMedia, on_delete=models.CASCADE, related_name="posts")
    categories = models.ManyToManyField(Category, related_name="posts")
    caption = models.TextField()  # Text for the post's caption or message
    image = models.ImageField(upload_to="post_images/")
    link = models.URLField(blank=True, null=True)  # Optional URL (e.g., link to a website)
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for when the post was created
    posted_at = models.DateTimeField(blank=True, null=True) # Timestamp when post is published
    scheduled_at = models.DateTimeField(blank=True, null=True) # Timestamp for when the post is scheduled to be published
    status = models.CharField(
        max_length=20,
        choices=POST_STATUS_OPTIONS,
        default='scheduled',
    )
    reactions = models.IntegerField(default=0) # Store number of reactions (likes, etc.)
    comments = models.IntegerField(default=0) # Store number of comments
    reposts = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Post: {self.categories} - {self.caption}"

    class Meta:
        ordering = ['-created_at']
