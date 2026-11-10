"""
analytics/urls.py

URL routing for LabCraft Analytics & Reporting Module.

All routes are mounted under /api/analytics/ in config/urls.py.

Routes:
  - GET /api/analytics/student/dashboard/     -> Student dashboard metrics
  - GET /api/analytics/teacher/dashboard/     -> Teacher multi-classroom metrics
  - GET /api/analytics/classroom/<id>/        -> Classroom analytics & leaderboard
  - GET /api/analytics/assignment/<id>/       -> Assignment metrics & gradebook
"""

from django.urls import path
from .views import (
    StudentDashboardAnalyticsView,
    TeacherDashboardAnalyticsView,
    ClassroomAnalyticsView,
    AssignmentAnalyticsView,
)

urlpatterns = [
    # Student platform dashboard
    path(
        'student/dashboard/',
        StudentDashboardAnalyticsView.as_view(),
        name='student-analytics-dashboard'
    ),

    # Teacher platform overview
    path(
        'teacher/dashboard/',
        TeacherDashboardAnalyticsView.as_view(),
        name='teacher-analytics-dashboard'
    ),

    # Detailed classroom analytics & student leaderboard
    path(
        'classroom/<int:classroom_id>/',
        ClassroomAnalyticsView.as_view(),
        name='classroom-analytics'
    ),

    # Detailed assignment outcomes & gradebook
    path(
        'assignment/<int:assignment_id>/',
        AssignmentAnalyticsView.as_view(),
        name='assignment-analytics'
    ),
]
