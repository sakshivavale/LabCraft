"""
grader/admin.py

Django Admin configuration for Test Cases and Grading Results.
"""

from django.contrib import admin
from .models import TestCase, GradingResult


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'assignment',
        'is_hidden',
        'time_limit',
        'memory_limit',
        'created_at',
    ]
    list_filter = ['is_hidden', 'time_limit', 'created_at']
    search_fields = ['assignment__title', 'input_data', 'expected_output']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Assignment & Visibility', {
            'fields': ('assignment', 'is_hidden'),
        }),
        ('Test Data (I/O)', {
            'fields': ('input_data', 'expected_output'),
        }),
        ('Execution Limits', {
            'fields': ('time_limit', 'memory_limit'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(GradingResult)
class GradingResultAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'submission',
        'status',
        'passed_count',
        'total_count',
        'score',
        'created_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['submission__student__username', 'submission__assignment__title']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Submission Info', {
            'fields': ('submission', 'status', 'score'),
        }),
        ('Test Case Metrics', {
            'fields': ('passed_count', 'total_count'),
        }),
        ('Execution Logs', {
            'fields': ('execution_log', 'error_message'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
