"""
classrooms/urls.py

URL routing for the Classroom Management module.
All these paths are mounted under /api/classrooms/ in config/urls.py.

Summary of endpoints:
  Teacher endpoints:
    GET  /api/classrooms/           → list own classrooms
    POST /api/classrooms/           → create a classroom
    GET  /api/classrooms/<id>/      → view classroom details
    PUT  /api/classrooms/<id>/      → update classroom
    PATCH /api/classrooms/<id>/     → partial update
    DELETE /api/classrooms/<id>/    → delete classroom
    GET  /api/classrooms/<id>/students/ → list students in classroom

  Student endpoints:
    POST   /api/classrooms/join/        → join a classroom by code
    GET    /api/classrooms/my/          → view joined classrooms
    GET    /api/classrooms/<id>/detail/ → view a joined classroom's detail
    DELETE /api/classrooms/<id>/leave/  → leave a classroom
"""

from django.urls import path
from .views import (
    ClassroomListCreateView,
    ClassroomDetailView,
    ClassroomStudentListView,
    JoinClassroomView,
    MyClassroomsView,
    LeaveClassroomView,
    ClassroomDetailForStudentView,
)

urlpatterns = [

    # ------------------------------------------------------------------
    # TEACHER ENDPOINTS
    # ------------------------------------------------------------------

    # GET  /api/classrooms/      → teacher lists their classrooms
    # POST /api/classrooms/      → teacher creates a classroom
    path('', ClassroomListCreateView.as_view(), name='classroom-list-create'),

    # GET    /api/classrooms/<id>/  → view classroom details (with student list)
    # PATCH  /api/classrooms/<id>/  → update name, description, is_active
    # DELETE /api/classrooms/<id>/  → delete the classroom
    path('<int:pk>/', ClassroomDetailView.as_view(), name='classroom-detail'),

    # GET /api/classrooms/<id>/students/  → list all students in this classroom
    path('<int:pk>/students/', ClassroomStudentListView.as_view(), name='classroom-students'),

    # ------------------------------------------------------------------
    # STUDENT ENDPOINTS
    # ------------------------------------------------------------------

    # POST /api/classrooms/join/  → body: { "join_code": "A3F2D1B4" }
    # Joins the student to the classroom with that code
    path('join/', JoinClassroomView.as_view(), name='classroom-join'),

    # GET /api/classrooms/my/  → list all classrooms this student has joined
    path('my/', MyClassroomsView.as_view(), name='my-classrooms'),

    # GET /api/classrooms/<id>/detail/  → view details of a classroom the student joined
    path('<int:pk>/detail/', ClassroomDetailForStudentView.as_view(), name='classroom-detail-student'),

    # DELETE /api/classrooms/<id>/leave/  → student leaves a classroom
    path('<int:pk>/leave/', LeaveClassroomView.as_view(), name='classroom-leave'),
]
