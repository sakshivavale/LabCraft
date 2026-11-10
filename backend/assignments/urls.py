"""
assignments/urls.py

URL routing for the Assignment Management module.

All URLs are mounted under /api/assignments/ in the main config/urls.py.

Teacher endpoints  (require approved teacher login):
  GET/POST /api/assignments/classroom/<id>/         → list or create assignments
  GET/PATCH/DELETE /api/assignments/<id>/           → view, update, or delete one assignment

Student endpoints  (require student login):
  GET /api/assignments/classroom/<id>/student/      → list published assignments in a joined classroom
  GET /api/assignments/<id>/student/                → view one published assignment
"""

from django.urls import path
from .views import (
    TeacherAssignmentListCreateView,
    TeacherAssignmentDetailView,
    StudentAssignmentListView,
    StudentAssignmentDetailView,
)

# WHY name each URL?
# Names (like 'assignment-list-create') let us reference URLs in tests and code
# using reverse('assignment-list-create') instead of hardcoding the string.
# That way, if we change the URL later, we only change it in ONE place.
urlpatterns = [
    # ------------------------------------------------------------------
    # TEACHER ENDPOINTS
    # ------------------------------------------------------------------

    # List all assignments in a classroom / Create a new assignment
    # <int:classroom_id> tells Django to capture an integer from the URL
    # and pass it to the view as 'classroom_id'.
    path(
        'classroom/<int:classroom_id>/',
        TeacherAssignmentListCreateView.as_view(),
        name='assignment-list-create'
    ),

    # View / Update / Delete a specific assignment by its ID
    # <int:pk> is the assignment's primary key (database ID)
    path(
        '<int:pk>/',
        TeacherAssignmentDetailView.as_view(),
        name='assignment-detail'
    ),

    # ------------------------------------------------------------------
    # STUDENT ENDPOINTS
    # ------------------------------------------------------------------

    # List published assignments in a classroom the student has joined
    # NOTE: 'classroom/<id>/student/' must be declared BEFORE '<pk>/student/'
    # so Django doesn't confuse 'classroom' with an integer pk.
    path(
        'classroom/<int:classroom_id>/student/',
        StudentAssignmentListView.as_view(),
        name='student-assignment-list'
    ),

    # View one specific published assignment
    path(
        '<int:pk>/student/',
        StudentAssignmentDetailView.as_view(),
        name='student-assignment-detail'
    ),
]
