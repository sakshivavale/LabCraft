"""
grader/urls.py

URL routing for the Automated Grading Engine module.

All routes are mounted under /api/grader/ in config/urls.py.

Endpoints:
  Teacher & Student Test Cases:
    GET/POST  /api/grader/assignment/<id>/test-cases/
    GET/PATCH/DELETE /api/grader/test-cases/<id>/

  Evaluation & Results:
    POST /api/grader/submission/<id>/grade/
    GET  /api/grader/submission/<id>/result/
"""

from django.urls import path
from .views import (
    AssignmentTestCaseListCreateView,
    TestCaseDetailView,
    TriggerGradingView,
    GradingResultView,
)

urlpatterns = [
    # Assignment Test Cases (List & Create)
    path(
        'assignment/<int:assignment_id>/test-cases/',
        AssignmentTestCaseListCreateView.as_view(),
        name='assignment-testcases'
    ),

    # Single Test Case (Retrieve, Update, Delete)
    path(
        'test-cases/<int:pk>/',
        TestCaseDetailView.as_view(),
        name='testcase-detail'
    ),

    # Trigger Evaluation on a Submission
    path(
        'submission/<int:submission_id>/grade/',
        TriggerGradingView.as_view(),
        name='trigger-grading'
    ),

    # View Grading Result & Logs
    path(
        'submission/<int:submission_id>/result/',
        GradingResultView.as_view(),
        name='grading-result'
    ),
]
