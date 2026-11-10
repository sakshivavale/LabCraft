"""
classrooms/admin.py

Registers Classroom and ClassroomMembership with Django's Admin panel.
Admin staff can browse, search, and manage all classrooms and memberships
through the web interface at /admin/.
"""

from django.contrib import admin
from .models import Classroom, ClassroomMembership


# =============================================================================
# INLINE: Show memberships inside the Classroom admin page
# =============================================================================

class ClassroomMembershipInline(admin.TabularInline):
    """
    TabularInline shows ClassroomMembership records as a table
    embedded inside the Classroom detail page in Admin.

    This means when you open a Classroom in Admin, you can see
    all its students right there on the same page.
    """
    model = ClassroomMembership
    extra = 0            # don't show empty "add new" rows by default
    readonly_fields = ['student', 'joined_at']   # these cannot be edited from here
    can_delete = True    # admin can remove a student from the classroom


# =============================================================================
# CLASSROOM ADMIN
# =============================================================================

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    """Admin configuration for the Classroom model."""

    list_display  = ['name', 'teacher', 'join_code', 'student_count', 'is_active', 'created_at']
    list_filter   = ['is_active', 'created_at']
    search_fields = ['name', 'teacher__username', 'join_code']
    ordering      = ['-created_at']

    # join_code is auto-generated — admin should not change it
    readonly_fields = ['join_code', 'created_at', 'updated_at']

    # Show memberships (students) inline on the classroom detail page
    inlines = [ClassroomMembershipInline]

    fieldsets = [
        ('Classroom Info', {
            'fields': ('name', 'description', 'teacher', 'is_active')
        }),
        ('Join Code (auto-generated)', {
            'fields': ('join_code',),
            'classes': ('collapse',),   # collapsible section in Admin
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    ]

    def student_count(self, obj):
        """Display the number of students in the classroom list view."""
        return obj.student_count
    student_count.short_description = 'Students'


# =============================================================================
# CLASSROOM MEMBERSHIP ADMIN
# =============================================================================

@admin.register(ClassroomMembership)
class ClassroomMembershipAdmin(admin.ModelAdmin):
    """Admin configuration for ClassroomMembership."""

    list_display  = ['student', 'classroom', 'joined_at']
    list_filter   = ['classroom', 'joined_at']
    search_fields = ['student__username', 'classroom__name']
    readonly_fields = ['joined_at']
    ordering      = ['-joined_at']
