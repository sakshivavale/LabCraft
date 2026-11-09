"""
WSGI config for LabCraft project.

Exposes the WSGI callable as a module-level variable named ``application``.
Used by traditional web servers (Gunicorn, uWSGI) to serve the app.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

