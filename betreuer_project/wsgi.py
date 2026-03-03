"""
WSGI config for betreuer_project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "betreuer_project.settings.production",
)

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
