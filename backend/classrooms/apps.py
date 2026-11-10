"""
classrooms/apps.py

App configuration for the Classrooms module.

Django uses AppConfig classes to store metadata about each application.
The 'name' must match the app folder name exactly.
'default_auto_field' tells Django to use BigAutoField (64-bit integer)
as the default primary key type for all models in this app.
"""

from django.apps import AppConfig


class ClassroomsConfig(AppConfig):
    # Use a 64-bit integer as the default PK — supports much larger tables
    # than a 32-bit integer (2 billion vs 9 quintillion rows)
    default_auto_field = 'django.db.models.BigAutoField'

    # Must exactly match the app folder name so Django can find it
    name = 'classrooms'

    # Human-readable name shown in Django Admin
    verbose_name = 'Classroom Management'

