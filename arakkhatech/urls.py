"""
URL configuration for arakkhatech project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),

    # API
    path('api/v1/', include('courses.urls_api')),
    path('api/v1/', include('docs.urls_api')),

    # Website
    path('docs/', include('docs.urls')),
    path('', include('courses.urls')),

    # Authentication
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('allauth.urls')),
]


# ============================================================
# LOCAL MEDIA FILES
# ============================================================
# Only serve local media when Supabase is NOT being used.

# Local filesystem media only
if settings.DEBUG and not settings.SUPABASE_S3_ENDPOINT:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

# ============================================================
# CUSTOM 404
# ============================================================

handler404 = 'courses.views.preview_404'