"""
개발 환경 설정
"""
import os
from .base import *

DEBUG = os.getenv('DEBUG', 'True')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
# Security settings
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Development-specific apps
INSTALLED_APPS += [
    'django_extensions',  # 유용한 개발 도구
]

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'