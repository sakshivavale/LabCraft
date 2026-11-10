"""
submissions/apps.py

App configuration for the Code Editor & Submissions module.
"""

from django.apps import AppConfig


class SubmissionsConfig(AppConfig):
    # Django uses BigAutoField as the default primary key type for all models.
    default_auto_field = 'django.db.models.BigAutoField'

    # The app name must match the folder name exactly.
    name = 'submissions'

    # Human-readable name shown in Django Admin panel sidebar.
    verbose_name = 'Code Submissions'
