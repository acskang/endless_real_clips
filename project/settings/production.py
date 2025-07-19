"""
운영 환경 설정
"""
import os
from os.path import abspath, dirname, join
from dotenv import load_dotenv
from .base import *

current_dir = dirname(abspath(__file__))
env_dir = dirname(dirname(dirname(current_dir)))
DOTENV_PATH = join(env_dir, '.env_prod')
LOGGING_PATH = join(env_dir, 'logs/django.log')
load_dotenv(dotenv_path=DOTENV_PATH)

# Debugging and allowed hosts
DEBUG = os.getenv('DEBUG', '')
# ALLOWED_HOSTS 설정
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
# Security settings
SECRET_KEY = os.getenv('SECRET_KEY', '')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CORS settings for production
CORS_ALLOWED_ORIGINS = [
    "https://movie.thesysm.com",
    "https://ganzskang.pythonanywhere.com",
]

# Static files
STATIC_ROOT = '/home/ganzskang/endless_real_clips/static'

# Media files
MEDIA_ROOT = '/home/ganzskang/endless_real_clips/media'

# Email backend for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = os.getenv('EMAIL_PORT', 587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')


# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGGING_PATH,
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}