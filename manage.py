#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from dotenv import load_dotenv


def main():
    """Run administrative tasks."""
    if os.getenv('ENVIRONMENT') == 'development':
        print("Running in development mode")
        # Load environment variables from .env_local
        ENV_DIR = os.path.expanduser('~/ganzskang/endless_real_clips/dj/')
        DOTENV_PATH = os.path.join(ENV_DIR, '.env_local')
        load_dotenv(dotenv_path=DOTENV_PATH)
        # Load local settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.local')
    elif os.getenv('ENVIRONMENT') == 'production':
        print("Running in production mode")
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.production')
    else:
        print("Environment variable 'ENVIRONMENT' not set.")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
