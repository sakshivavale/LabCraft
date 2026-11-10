"""
grader/views.py

API Views for the Automated Grading Engine module.

Endpoints Provided:
  1. GET/POST  /api/grader/assignment/<assignment_id>/test-cases/
       - Teacher: List all test cases (public + hidden) or Create new test case.
       - Student: List public test cases only (is_hidden=False).
  2. GET/PATCH/DELETE /api/grader/test-cases/<pk>/
       - Teacher: View, update, or delete a test case in their classroom.
       - Student: Read-only access to public test cases.
  3. POST /api/grader/submission/<submission_id>/grade/
       - Trigger evaluation of a submission.
  4. GET  /api/grader/submission/<submission_id>/result/
       - Retrieve evaluation logs and score (sanitized for students).
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from accounts.permissions import IsApprovedTeacher, IsStudent
from classrooms.models import ClassroomMembership
from assignments.models import Assignment
from submissions.models import Submission

from .models import TestCase, GradingResult
from .serializers import (
    TestCaseTeacherSerializer,
    TestCaseStudentSerializer,
    GradingResultTeacherSerializer,
    GradingResultStudentSerializer,
)
from .engine import grade_submission


# =============================================================================
# 1. ASSIGNMENT TEST CASES: LIST & CREATE
# =============================================================================

class AssignmentTestCaseListCreateView(APIView):
    """
    GET:  List test cases for an assignment.
          - Teachers see all test cases (public + hidden).
          - Students only see public test cases (is_hidden=False).
    POST: Create a test case (Approved Teachers only).
    """

    def get(self, request, assignment_id):
        # 1. Check if user is an approved teacher for this classroom
        assignment = get_object_or_404(Assignment, id=assignment_id)

        if request.user.is_teacher and assignment.classroom.teacher == request.user:
            # Teacher: return all test cases with full serializer
            test_cases = assignment.test_cases.all().order_by('id')
            serializer = TestCaseTeacherSerializer(test_cases, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # 2. Check if user is an enrolled student
        if request.user.is_student:
            get_object_or_404(
                ClassroomMembership,
                student=request.user,
                classroom=assignment.classroom
            )
            # Student: return ONLY public test cases with student serializer
            test_cases = assignment.test_cases.filter(is_hidden=False).order_by('id')
            serializer = TestCaseStudentSerializer(test_cases, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Unrelated user
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, assignment_id):
        """Create a new test case for an assignment (Teacher only)."""
        # Teacher must be approved and own the classroom
        assignment = get_object_or_404(
            Assignment,
            id=assignment_id,
            classroom__teacher=request.user
        )

        serializer = TestCaseTeacherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test_case = serializer.save(assignment=assignment)

        return Response(
            TestCaseTeacherSerializer(test_case).data,
            status=status.HTTP_201_CREATED
        )


# =============================================================================
# 2. SINGLE TEST CASE: RETRIEVE, UPDATE, DELETE
# =============================================================================

class TestCaseDetailView(APIView):
    """
    GET:    View a specific test case (sanitized for students, full for teachers).
    PATCH:  Update test case (Teacher only).
    DELETE: Delete test case (Teacher only).
    """

    def get_test_case_and_verify(self, request, pk):
        """Helper to find test case and enforce classroom access permissions."""
        test_case = get_object_or_404(TestCase, pk=pk)
        assignment = test_case.assignment

        if request.user.is_teacher and assignment.classroom.teacher == request.user:
            return test_case, True  # (test_case, is_teacher_owner)

        if request.user.is_student:
            # Verify student is in classroom
            get_object_or_404(
                ClassroomMembership,
                student=request.user,
                classroom=assignment.classroom
            )
            # If test case is hidden, student cannot access it (404)
            if test_case.is_hidden:
                return None, False
            return test_case, False

        return None, False

    def get(self, request, pk):
        test_case, is_teacher_owner = self.get_test_case_and_verify(request, pk)
        if not test_case:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if is_teacher_owner:
            serializer = TestCaseTeacherSerializer(test_case)
        else:
            serializer = TestCaseStudentSerializer(test_case)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        test_case = get_object_or_404(
            TestCase,
            pk=pk,
            assignment__classroom__teacher=request.user
        )
        serializer = TestCaseTeacherSerializer(test_case, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(TestCaseTeacherSerializer(updated).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        test_case = get_object_or_404(
            TestCase,
            pk=pk,
            assignment__classroom__teacher=request.user
        )
        test_case.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 3. TRIGGER EVALUATION FOR A SUBMISSION
# =============================================================================

class TriggerGradingView(APIView):
    """
    POST /api/grader/submission/<submission_id>/grade/
    Triggers automated sandbox grading for a submission.

    Access:
      - The student who authored the submission.
      - The teacher who owns the assignment's classroom.
    """

    def post(self, request, submission_id):
        # 1. Fetch submission
        submission = get_object_or_404(Submission, id=submission_id)
        assignment = submission.assignment

        # 2. Permission check: student owner OR classroom teacher
        is_owner = (submission.student == request.user)
        is_teacher_owner = (
            request.user.is_teacher and
            assignment.classroom.teacher == request.user
        )

        if not (is_owner or is_teacher_owner):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        # 3. Run evaluation
        grading_result = grade_submission(submission.id)

        # 4. Return appropriate serialized result
        if is_teacher_owner:
            serializer = GradingResultTeacherSerializer(grading_result)
        else:
            serializer = GradingResultStudentSerializer(grading_result)

        return Response(
            {
                'message': f'Evaluation complete. Status: {grading_result.status}',
                'result': serializer.data,
            },
            status=status.HTTP_200_OK
        )


# =============================================================================
# 4. VIEW GRADING RESULT & EXECUTION LOGS
# =============================================================================

class GradingResultView(APIView):
    """
    GET /api/grader/submission/<submission_id>/result/
    Retrieves grading result, test breakdowns, and score for a submission.

    Security:
      - Teacher receives full execution logs including hidden test cases.
      - Students receive sanitized logs (hidden test case details are redacted).
      - Other users receive 404 Not Found.
    """

    def get(self, request, submission_id):
        submission = get_object_or_404(Submission, id=submission_id)
        assignment = submission.assignment

        is_owner = (submission.student == request.user)
        is_teacher_owner = (
            request.user.is_teacher and
            assignment.classroom.teacher == request.user
        )

        if not (is_owner or is_teacher_owner):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        grading_result = getattr(submission, 'grading_result', None)
        if not grading_result:
            return Response(
                {
                    'status': submission.status,
                    'message': 'This submission has not been evaluated yet or grading is currently running.',
                    'feedback': submission.feedback,
                },
                status=status.HTTP_200_OK
            )

        if is_teacher_owner:
            serializer = GradingResultTeacherSerializer(grading_result)
        else:
            serializer = GradingResultStudentSerializer(grading_result)

        return Response(serializer.data, status=status.HTTP_200_OK)
