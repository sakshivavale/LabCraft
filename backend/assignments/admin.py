"""
assignments/admin.py

Django Admin registration for the Assignment model.

Registering Assignment in Admin lets us:
  - Browse all assignments in the Django Admin panel.
  - Create, edit, and delete assignments directly (useful for testing & moderation).
  - Filter and search assignments easily.
"""

from django.contrib import admin
from .models import Assignment


# =============================================================================
# ASSIGNMENT ADMIN
# =============================================================================

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """
    Customizes how assignments appear and behave in the Django Admin.
    """

    # Columns shown in the list view (the table of all assignments)
    list_display = [
        'title',
        'classroom',
        'created_by',
        'language',
        'difficulty',
        'is_published',
        'due_date',
        'created_at',
    ]

    # Sidebar filters — click to narrow down the list
    list_filter = [
        'is_published',   # show only drafts or only published
        'language',       # filter by programming language
        'difficulty',     # filter by easy/medium/hard
        'created_at',     # filter by creation date
    ]

    # Search box — searches across these fields
    search_fields = [
        'title',                   # search by assignment title
        'classroom__name',         # search by classroom name (double underscore = FK lookup)
        'created_by__username',    # search by teacher's username
    ]

    # Fields that cannot be edited in Admin — they are auto-set or computed
    readonly_fields = [
        'created_at',   # auto-set when created (auto_now_add)
        'updated_at',   # auto-set every time saved (auto_now)
        'is_past_due',  # @property — computed, cannot be stored
        'status',       # @property — computed, cannot be stored
    ]

    # Fieldsets group related fields together in the edit/add form
    # WHY use fieldsets? A flat form with 12 fields is confusing.
    # Grouping makes it clear which fields belong together.
    fieldsets = (
        # Group 1: Basic identification
        ('Assignment Info', {
            'fields': ('title', 'classroom', 'created_by')
        }),

        # Group 2: The actual content of the assignment
        ('Content', {
            'fields': ('description', 'instructions'),
            'classes': ('collapse',),   # collapsed by default to save space
        }),

        # Group 3: Settings that control assignment behaviour
        ('Settings', {
            'fields': ('language', 'difficulty', 'max_marks', 'due_date', 'is_published')
        }),

        # Group 4: Computed properties (read-only display)
        ('Status', {
            'fields': ('status', 'is_past_due'),
            'classes': ('collapse',),
        }),

        # Group 5: Auto-managed timestamps
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
