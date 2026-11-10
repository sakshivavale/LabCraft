"""
assignments/apps.py

App configuration for the Assignment Management module.

Django reads this class to understand how this app is configured.
verbose_name is what Django Admin shows as the app's display name.
"""

from django.apps import AppConfig


class AssignmentsConfig(AppConfig):
    # Django uses BigAutoField as the default primary key type for all models in this app.
    # WHY BigAutoField? It supports up to 9.2 quintillion rows — future-proof.
    default_auto_field = 'django.db.models.BigAutoField'

    # The app name must match the folder name exactly.
    # Django uses this to find the app's models, views, URLs, etc.
    name = 'assignments'

    # Human-readable name shown in Django Admin panel sidebar.
    verbose_name = 'Assignment Management'
