
# dj/project/urls.py
# This file is part of the Django project configuration for URL routing.
# It includes the admin interface, app-specific URLs, and static file serving.
# It is designed to handle requests to the admin site, the main application, and API endpoints.
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('phrase.urls')),
    path('api/', include('api.urls')),  
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# 미디어 파일 서빙 (개발환경용)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)