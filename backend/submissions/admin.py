"""
submissions/admin.py

Django Admin registration for the Submission model.

Registering Submission in Admin lets us:
  - Browse all submissions in the Django Admin panel.
  - Review student code, status, and feedback directly.
  - Useful for moderation, debugging, and testing Module 5 grader integration.
"""

from django.contrib import admin
from .models import Submission


# =============================================================================
# SUBMISSION ADMIN
# =============================================================================

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    """
    Customizes how submissions appear and behave in Django Admin.
    """

    # Columns shown in the list table of all submissions
    list_display = [
        'id',
        'student',
        'assignment',
        'language',
        'status',
        'is_late',      # @property — shows if submitted after deadline
        'submitted_at',
    ]

    # Sidebar filters — click to narrow the list
    list_filter = [
        'status',         # filter by grading status
        'language',       # filter by programming language
        'submitted_at',   # filter by submission date
    ]

    # Search box — searches across these fields
    search_fields = [
        'student__username',      # search by student username
        'assignment__title',      # search by assignment title
        'assignment__classroom__name',  # search by classroom name
    ]

    # Fields that cannot be edited — either auto-set or computed
    readonly_fields = [
        'submitted_at',   # auto-set when created (auto_now_add)
        'is_late',        # @property — computed, not stored
    ]

    # Fieldsets group related fields in the edit/add form
    fieldsets = (
        # Group 1: Who submitted what
        ('Submission Info', {
            'fields': ('student', 'assignment', 'language', 'submitted_at')
        }),

        # Group 2: The submitted code
        ('Source Code', {
            'fields': ('source_code',),
        }),

        # Group 3: Grading status and feedback
        ('Grading', {
            'fields': ('status', 'feedback', 'is_late'),
        }),
    )
