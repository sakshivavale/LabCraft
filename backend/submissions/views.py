"""
submissions/views.py

API views for the Code Editor & Submissions module.

Who can do what:
  - Student: submit code for a published assignment in a joined classroom.
             View their own submission history and submission details.
  - Approved Teacher: view all submissions for assignments in their classrooms.
  - Nobody: execute code directly (that is Module 5 — Docker grader).

Security rules enforced here:
  1. Students can only submit to published, non-expired assignments.
  2. Students can only submit to classrooms they have joined.
  3. Students can only view THEIR OWN submissions.
  4. Teachers can only view submissions in THEIR OWN classrooms.
  5. No cross-student or cross-classroom data leaks.
"""

from rest_framework import generics, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.permissions import IsApprovedTeacher, IsStudent   # reuse from Module 1
from classrooms.models import ClassroomMembership               # reuse from Module 2
from assignments.models import Assignment                       # reuse from Module 3
from .models import Submission
from .serializers import (
    SubmissionListSerializer,
    SubmissionDetailSerializer,
    SubmissionCreateSerializer,
)


# =============================================================================
# 1. STUDENT: SUBMIT CODE FOR AN ASSIGNMENT
#    POST /api/submissions/assignment/<assignment_id>/submit/
# =============================================================================

class SubmitCodeView(generics.CreateAPIView):
    """
    Allows a student to submit their code for a specific assignment.

    What this view does:
      1. Checks the student is authenticated and has 'student' role.
      2. Finds the assignment by ID — it must be published.
      3. Verifies the student is a member of the assignment's classroom.
      4. Checks the deadline has not passed.
      5. Validates the source code and language.
      6. Creates and stores the Submission record.
      7. Returns the submission details with a success message.
    """
    permission_classes = [IsStudent]
    serializer_class = SubmissionCreateSerializer

    def create(self, request, *args, **kwargs):
        """
        Override create() to inject assignment + student from context/JWT,
        and to run all our business-logic checks BEFORE saving.

        WHY override instead of using perform_create()?
          We need to pass the assignment object via serializer context
          for language validation, AND we return a custom response.
          Doing all this in create() keeps the logic in one place.
        """
        assignment_id = self.kwargs['assignment_id']   # from URL

        # ------------------------------------------------------------------
        # STEP 1: Get the assignment.
        # It must exist AND be published (is_published=True).
        # WHY check is_published? Students shouldn't submit to draft assignments
        # that the teacher hasn't released yet.
        # ------------------------------------------------------------------
        assignment = get_object_or_404(
            Assignment,
            id=assignment_id,
            is_published=True    # only published assignments accept submissions
        )

        # ------------------------------------------------------------------
        # STEP 2: Check the student is a member of this classroom.
        # get_object_or_404 → 404 if not a member (not 403).
        # WHY 404? Same reason as Module 3: 404 reveals nothing about the assignment.
        # ------------------------------------------------------------------
        get_object_or_404(
            ClassroomMembership,
            student=request.user,
            classroom=assignment.classroom
        )

        # ------------------------------------------------------------------
        # STEP 3: Check the deadline has not passed.
        # WHY enforce deadline in the view (not the model)?
        #   The model is agnostic — the grader in Module 5 needs to update
        #   existing submissions even after the deadline.
        #   The view is the right place to block NEW submissions.
        # ------------------------------------------------------------------
        if assignment.due_date and timezone.now() > assignment.due_date:
            return Response(
                {
                    'error': (
                        f'The deadline for "{assignment.title}" has passed '
                        f'({assignment.due_date.strftime("%d %b %Y, %I:%M %p")}). '
                        'No more submissions are accepted.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ------------------------------------------------------------------
        # STEP 4: Validate the submitted data (source_code, language).
        # Pass assignment via context so validate() can check the language.
        # ------------------------------------------------------------------
        serializer = self.get_serializer(
            data=request.data,
            context={'assignment': assignment, 'request': request}  # extra context for validation
        )
        serializer.is_valid(raise_exception=True)

        # ------------------------------------------------------------------
        # STEP 5: Save the submission.
        # Inject assignment and student — these are NOT from request.data.
        # The student CANNOT fake their identity or the target assignment.
        # Save only once — no perform_create() pattern to avoid double-save.
        # ------------------------------------------------------------------
        submission = serializer.save(
            assignment=assignment,
            student=request.user     # from JWT token — cannot be forged
        )

        return Response(
            {
                'message': (
                    f'Your code for "{assignment.title}" has been submitted successfully. '
                    'Status: Pending grading.'
                ),
                'submission': SubmissionDetailSerializer(submission).data,
            },
            status=status.HTTP_201_CREATED
        )


# =============================================================================
# 2. STUDENT: VIEW OWN SUBMISSION HISTORY FOR AN ASSIGNMENT
#    GET /api/submissions/assignment/<assignment_id>/my/
# =============================================================================

class MySubmissionListView(generics.ListAPIView):
    """
    Returns a list of all submissions made by the logged-in student
    for a specific assignment.

    WHY show history? Students often resubmit to improve their score.
    Seeing the history helps them track their attempts and progress.
    """
    permission_classes = [IsStudent]
    serializer_class = SubmissionListSerializer

    def get_queryset(self):
        """
        SECURITY: Return only submissions where:
          - assignment matches the URL parameter
          - student == the logged-in user (never see other students' code)
        """
        assignment_id = self.kwargs['assignment_id']

        # Verify the assignment exists and is published
        assignment = get_object_or_404(
            Assignment, id=assignment_id, is_published=True
        )

        # Verify the student is a member of the classroom
        get_object_or_404(
            ClassroomMembership,
            student=self.request.user,
            classroom=assignment.classroom
        )

        # Return only THIS student's submissions for this assignment
        return Submission.objects.filter(
            assignment=assignment,
            student=self.request.user     # NEVER show other students' submissions
        )


# =============================================================================
# 3. STUDENT: VIEW DETAIL OF ONE SPECIFIC SUBMISSION
#    GET /api/submissions/<id>/
# =============================================================================

class SubmissionDetailView(generics.RetrieveAPIView):
    """
    Allows a student to view the full details of one of their own submissions.
    Includes source code and grader feedback.

    SECURITY: get_queryset() filters by student=request.user.
    A student trying to access another student's submission ID gets 404.
    """
    permission_classes = [IsStudent]
    serializer_class = SubmissionDetailSerializer

    def get_queryset(self):
        """
        Return only submissions that belong to the logged-in student.
        Students CANNOT view other students' source code — ever.
        """
        return Submission.objects.filter(student=self.request.user)


# =============================================================================
# 4. TEACHER: VIEW ALL SUBMISSIONS FOR AN ASSIGNMENT
#    GET /api/submissions/assignment/<assignment_id>/all/
# =============================================================================

class TeacherSubmissionListView(generics.ListAPIView):
    """
    Allows an approved teacher to view ALL submissions for a specific assignment
    in one of their classrooms.

    WHY teachers need this:
      - To review student progress
      - To identify students who haven't submitted yet
      - The Module 5 grader also uses this data for analytics

    SECURITY: The assignment must be in a classroom owned by this teacher.
    """
    permission_classes = [IsApprovedTeacher]
    serializer_class = SubmissionDetailSerializer   # full detail including source code

    def get_queryset(self):
        """
        1. Find the assignment — it must be in one of this teacher's classrooms.
        2. Return all submissions for that assignment.

        The double FK check (assignment__classroom__teacher=request.user)
        ensures a teacher can't snoop on another teacher's submissions.
        """
        assignment_id = self.kwargs['assignment_id']

        # Verify this assignment belongs to a classroom owned by this teacher
        assignment = get_object_or_404(
            Assignment,
            id=assignment_id,
            classroom__teacher=self.request.user    # MUST be this teacher's classroom
        )

        return Submission.objects.filter(assignment=assignment)


# =============================================================================
# 5. TEACHER: VIEW SUBMISSIONS BY STUDENT FOR AN ASSIGNMENT
#    GET /api/submissions/assignment/<assignment_id>/student/<student_id>/
# =============================================================================

class TeacherStudentSubmissionView(generics.ListAPIView):
    """
    Allows a teacher to view all submissions by a SPECIFIC student
    for a specific assignment.

    Use case: Teacher wants to review one student's attempt history.
    """
    permission_classes = [IsApprovedTeacher]
    serializer_class = SubmissionDetailSerializer

    def get_queryset(self):
        """
        Return submissions filtered by both assignment AND student.
        Security: assignment must be in teacher's classroom.
        """
        assignment_id = self.kwargs['assignment_id']
        student_id = self.kwargs['student_id']

        # Verify this assignment belongs to a classroom owned by this teacher
        assignment = get_object_or_404(
            Assignment,
            id=assignment_id,
            classroom__teacher=self.request.user
        )

        return Submission.objects.filter(
            assignment=assignment,
            student__id=student_id    # filter by specific student
        )
