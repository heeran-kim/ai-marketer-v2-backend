from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name='health_check'),
    path("api/users/", include('users.urls')),
    path("api/dashboard/", include("businesses.dashboard_urls")),
    path("api/businesses/", include("businesses.urls")),
    path("api/social/", include("social.urls")),
    path("api/posts/", include("posts.urls")),
    path("api/promotions/", include("promotions.urls")),
    path("api/ai/", include("ai.urls")),
    path("api/sales/", include('sales.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)