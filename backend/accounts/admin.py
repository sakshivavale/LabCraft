"""
accounts/admin.py

Registers the User model with Django's built-in Admin panel.

Django Admin (/admin/) is a ready-made web interface where
staff members can view and manage database records.

We extend the default UserAdmin to:
  - Show our custom fields (role, is_approved) in the list view.
  - Add a one-click "Approve selected teachers" bulk action.
"""

from django.contrib import admin                                 # admin site tools
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin  # Django's built-in User admin
from django.utils.translation import gettext_lazy as _          # for translatable labels

from .models import User


@admin.register(User)   # decorator: registers User with the admin site
class UserAdmin(BaseUserAdmin):
    """
    Customised admin view for LabCraft's User model.
    Inherits all standard Django user admin functionality and adds our extras.
    """

    # Columns shown in the user list table in Admin
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'role',          # 'student' or 'teacher'
        'is_approved',   # True/False
        'is_active',     # active account?
        'is_staff',      # Django admin access?
        'date_joined',
    ]

    # Sidebar filters in the Admin list view
    list_filter = [
        'role',
        'is_approved',
        'is_active',
        'is_staff',
    ]

    # Search bar: searches these fields
    search_fields = ['username', 'email', 'first_name', 'last_name']

    # Default ordering in Admin list (most recent first)
    ordering = ['-date_joined']

    # Clicking a user opens the detail page; these are the section layouts:
    # BaseUserAdmin.fieldsets already has: Personal info, Permissions, Important dates
    # We append our LabCraft-specific section
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('LabCraft Info'), {
            'fields': ('role', 'is_approved'),
            'description': (
                'Set the user\'s role and approval status. '
                'Teachers with is_approved=False cannot log in.'
            ),
        }),
    )

    # Layout for the "Add User" page in Admin
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('LabCraft Info'), {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'is_approved'),
        }),
    )

    # Bulk actions in the Admin list (checkbox → action)
    actions = ['approve_selected_teachers', 'revoke_selected_teachers']

    def approve_selected_teachers(self, request, queryset):
        """
        Bulk action: tick multiple teachers in Admin → select this action → approve all.
        queryset is the set of selected users.
        """
        # Only update users who are teachers (ignore students in the selection)
        updated_count = queryset.filter(role=User.Role.TEACHER).update(is_approved=True)
        self.message_user(
            request,
            f'{updated_count} teacher(s) approved successfully.'
        )

    approve_selected_teachers.short_description = 'Approve selected teachers'

    def revoke_selected_teachers(self, request, queryset):
        """Bulk action: revoke approval for selected teachers."""
        updated_count = queryset.filter(role=User.Role.TEACHER).update(is_approved=False)
        self.message_user(
            request,
            f'Approval revoked for {updated_count} teacher(s).'
        )

    revoke_selected_teachers.short_description = 'Revoke approval for selected teachers'
