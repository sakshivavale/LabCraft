"""
accounts/urls.py

Maps URL paths to views for the Accounts & Authentication module.

These URLs are mounted under /api/auth/ in config/urls.py.
So the full path is: /api/auth/<path defined here>

How URL routing works:
  Browser/frontend sends a request to a URL →
  Django checks this file →
  Calls the matching view →
  View returns a JSON response.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView  # built-in token refresh

from .views import (
    LoginView,
    StudentRegisterView,
    TeacherRegisterView,
    UserProfileView,
    PendingTeacherListView,
    ApproveTeacherView,
    RevokeTeacherView,
)

urlpatterns = [

    # ------------------------------------------------------------------
    # REGISTRATION
    # ------------------------------------------------------------------

    # POST /api/auth/register/student/
    # Body: { username, email, first_name, last_name, password, password2 }
    # Returns: { message, user }   — student is immediately active
    path('register/student/', StudentRegisterView.as_view(), name='student-register'),

    # POST /api/auth/register/teacher/
    # Body: { username, email, first_name, last_name, password, password2 }
    # Returns: { message, user }   — teacher must wait for admin approval
    path('register/teacher/', TeacherRegisterView.as_view(), name='teacher-register'),

    # ------------------------------------------------------------------
    # AUTHENTICATION (JWT tokens)
    # ------------------------------------------------------------------

    # POST /api/auth/login/
    # Body: { username, password }
    # Returns: { access, refresh, user }
    # - 'access'  → short-lived token (60 min), put in Authorization header
    # - 'refresh' → long-lived token (7 days), use to get new access token
    path('login/', LoginView.as_view(), name='token-obtain-pair'),

    # POST /api/auth/token/refresh/
    # Body: { refresh }
    # Returns: { access }   — gives a fresh access token without re-logging-in
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # ------------------------------------------------------------------
    # USER PROFILE
    # ------------------------------------------------------------------

    # GET    /api/auth/profile/   → view own profile (read all fields)
    # PUT    /api/auth/profile/   → replace first_name, last_name, email
    # PATCH  /api/auth/profile/   → update only some of those fields
    # Requires: Authorization: Bearer <access_token>
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    # ------------------------------------------------------------------
    # ADMIN: TEACHER APPROVAL (only Django admin/staff users)
    # ------------------------------------------------------------------

    # GET /api/auth/admin/teachers/pending/
    # Returns: list of teachers with is_approved=False
    path(
        'admin/teachers/pending/',
        PendingTeacherListView.as_view(),
        name='pending-teachers'
    ),

    # PATCH /api/auth/admin/teachers/<pk>/approve/
    # Sets is_approved=True for teacher with given primary key
    path(
        'admin/teachers/<int:pk>/approve/',
        ApproveTeacherView.as_view(),
        name='approve-teacher'
    ),

    # PATCH /api/auth/admin/teachers/<pk>/revoke/
    # Sets is_approved=False — removes login access for the teacher
    path(
        'admin/teachers/<int:pk>/revoke/',
        RevokeTeacherView.as_view(),
        name='revoke-teacher'
    ),
]
