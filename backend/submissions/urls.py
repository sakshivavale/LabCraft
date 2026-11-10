"""
submissions/urls.py

URL routing for the Code Editor & Submissions module.

All URLs are mounted under /api/submissions/ in the main config/urls.py.

Student endpoints (require student login):
  POST /api/submissions/assignment/<id>/submit/        → submit code
  GET  /api/submissions/assignment/<id>/my/            → view own history
  GET  /api/submissions/<id>/                          → view one submission detail

Teacher endpoints (require approved teacher login):
  GET  /api/submissions/assignment/<id>/all/                     → all submissions for assignment
  GET  /api/submissions/assignment/<id>/student/<student_id>/    → specific student's submissions
"""

from django.urls import path
from .views import (
    SubmitCodeView,
    MySubmissionListView,
    SubmissionDetailView,
    TeacherSubmissionListView,
    TeacherStudentSubmissionView,
)

# WHY name each URL?
# Using reverse('submission-submit', kwargs={'assignment_id': 1}) in tests and code
# means we don't hardcode URL strings — changes to URLs only need updating once.
urlpatterns = [
    # ------------------------------------------------------------------
    # STUDENT ENDPOINTS
    # ------------------------------------------------------------------

    # Submit code for an assignment
    # POST: student submits source_code + language
    path(
        'assignment/<int:assignment_id>/submit/',
        SubmitCodeView.as_view(),
        name='submission-submit'
    ),

    # View own submission history for a specific assignment
    # GET: returns list of this student's submissions (newest first)
    path(
        'assignment/<int:assignment_id>/my/',
        MySubmissionListView.as_view(),
        name='my-submission-list'
    ),

    # View full detail of one specific submission (own only)
    # GET: returns source code + status + feedback
    path(
        '<int:pk>/',
        SubmissionDetailView.as_view(),
        name='submission-detail'
    ),

    # ------------------------------------------------------------------
    # TEACHER ENDPOINTS
    # ------------------------------------------------------------------

    # View ALL submissions for one assignment in teacher's classroom
    # GET: teacher reviews all students' submissions
    path(
        'assignment/<int:assignment_id>/all/',
        TeacherSubmissionListView.as_view(),
        name='teacher-submission-list'
    ),

    # View all submissions by a SPECIFIC student for one assignment
    # GET: teacher reviews one student's submission history
    path(
        'assignment/<int:assignment_id>/student/<int:student_id>/',
        TeacherStudentSubmissionView.as_view(),
        name='teacher-student-submissions'
    ),
]
