"""
WSGI config for project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from dotenv import load_dotenv

# .env_local 경로 지정
ENV_DIR = os.path.expanduser('~/ganzskang/endless_real_clips/')
DOTENV_PATH = os.path.join(ENV_DIR, '.env_prod')

# 해당 경로에서 .env 로드
load_dotenv(dotenv_path=DOTENV_PATH)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.production')

application = get_wsgi_application()
