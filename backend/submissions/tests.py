"""
submissions/tests.py

Tests for the Code Editor & Submissions module.

Run these tests with:
  cd backend
  python manage.py test submissions -v 2

Run ALL module tests together with:
  python manage.py test accounts classrooms assignments submissions -v 2

Test classes:
  1. SubmissionModelTest            — model fields, is_late property, __str__
  2. SubmitCodeTest                 — POST submit code, all validation cases
  3. DeadlineEnforcementTest        — submission before/after deadline
  4. MySubmissionListTest           — student views own history
  5. SubmissionDetailTest           — student views one submission detail
  6. TeacherSubmissionViewTest      — teacher views all submissions
  7. TeacherStudentSubmissionTest   — teacher views specific student's submissions
  8. SubmissionSecurityTest         — cross-student, cross-teacher access denied
  9. SubmissionPermissionTest       — role-based, unauthenticated, wrong role
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from classrooms.models import Classroom, ClassroomMembership
from assignments.models import Assignment
from .models import Submission

User = get_user_model()


# =============================================================================
# HELPER FUNCTIONS — create common objects quickly in tests
# =============================================================================

def make_student(username, email=None, password='StrongPass123!'):
    """Create a student user with approved status."""
    return User.objects.create_user(
        username=username,
        email=email or f'{username}@test.com',
        password=password,
        role=User.Role.STUDENT,
        is_approved=True,
    )

def make_teacher(username, email=None, password='StrongPass123!', approved=True):
    """Create a teacher user, approved by default."""
    return User.objects.create_user(
        username=username,
        email=email or f'{username}@test.com',
        password=password,
        role=User.Role.TEACHER,
        is_approved=approved,
    )

def make_classroom(teacher, name='Test Classroom'):
    """Create a classroom owned by the given teacher."""
    return Classroom.objects.create(teacher=teacher, name=name)

def make_assignment(classroom, teacher, title='Test Assignment', published=True, **kwargs):
    """
    Create a published assignment by default.
    Pass published=False for draft assignments.
    Pass extra kwargs like due_date=... for specific scenarios.
    """
    return Assignment.objects.create(
        classroom=classroom,
        created_by=teacher,
        title=title,
        is_published=published,
        **kwargs
    )

def make_submission(assignment, student, source_code='print("hello")', language='python'):
    """Create a submission directly (bypassing the view — for model tests)."""
    return Submission.objects.create(
        assignment=assignment,
        student=student,
        source_code=source_code,
        language=language,
    )

def enroll(student, classroom):
    """Enroll a student in a classroom."""
    return ClassroomMembership.objects.create(student=student, classroom=classroom)


# =============================================================================
# 1. MODEL TESTS
# =============================================================================

class SubmissionModelTest(TestCase):
    """Tests for the Submission model's fields, properties, and string representation."""

    def setUp(self):
        """Set up teacher, student, classroom, and assignment for all model tests."""
        self.teacher = make_teacher('model_teacher')
        self.student = make_student('model_student')
        self.classroom = make_classroom(self.teacher, 'Model Lab')
        enroll(self.student, self.classroom)
        self.assignment = make_assignment(self.classroom, self.teacher, 'Model Assignment')

    def test_submission_created_with_correct_defaults(self):
        """
        Creating a submission should auto-set:
        status='pending', submitted_at=now, feedback=''
        """
        submission = make_submission(self.assignment, self.student)
        self.assertEqual(submission.student, self.student)
        self.assertEqual(submission.assignment, self.assignment)
        self.assertEqual(submission.source_code, 'print("hello")')
        self.assertEqual(submission.language, 'python')
        self.assertEqual(submission.status, 'pending')     # default
        self.assertEqual(submission.feedback, '')           # empty default
        self.assertIsNotNone(submission.submitted_at)

    def test_str_returns_readable_format(self):
        """__str__ should return 'student → assignment (status)'."""
        submission = make_submission(self.assignment, self.student)
        expected = f"model_student → Model Assignment (pending)"
        self.assertEqual(str(submission), expected)

    def test_is_late_false_when_no_due_date(self):
        """
        If assignment has no due_date, is_late must be False.
        No deadline = submissions are always on time.
        """
        submission = make_submission(self.assignment, self.student)
        self.assertFalse(submission.is_late)

    def test_is_late_false_when_submitted_before_deadline(self):
        """is_late is False when submitted before the assignment deadline."""
        future = timezone.now() + timedelta(days=7)
        assignment = make_assignment(
            self.classroom, self.teacher, 'Future Assignment', due_date=future
        )
        submission = make_submission(assignment, self.student)
        self.assertFalse(submission.is_late)

    def test_is_late_true_when_submitted_after_deadline(self):
        """
        is_late is True when submitted after the assignment deadline.
        We simulate this by creating an assignment with a past due_date,
        then directly creating a submission (bypassing view deadline check).
        """
        past = timezone.now() - timedelta(hours=1)
        # Create assignment with past due_date (directly in DB for testing)
        assignment = Assignment.objects.create(
            classroom=self.classroom,
            created_by=self.teacher,
            title='Expired Assignment',
            is_published=True,
            due_date=past
        )
        submission = Submission.objects.create(
            assignment=assignment,
            student=self.student,
            source_code='print("late")',
            language='python',
        )
        self.assertTrue(submission.is_late)

    def test_multiple_submissions_allowed(self):
        """
        A student can submit multiple times for the same assignment.
        There is NO unique constraint on (student, assignment) for submissions.
        Each resubmission is a separate record.
        """
        make_submission(self.assignment, self.student, 'print("attempt 1")')
        make_submission(self.assignment, self.student, 'print("attempt 2")')
        count = Submission.objects.filter(
            assignment=self.assignment, student=self.student
        ).count()
        self.assertEqual(count, 2)

    def test_ordering_newest_first(self):
        """Submissions should be ordered with the newest first (Meta.ordering)."""
        s1 = make_submission(self.assignment, self.student, 'first')
        s2 = make_submission(self.assignment, self.student, 'second')
        submissions = list(Submission.objects.filter(assignment=self.assignment))
        self.assertEqual(submissions[0], s2)   # second was newer
        self.assertEqual(submissions[1], s1)


# =============================================================================
# 2. SUBMIT CODE TESTS
# =============================================================================

class SubmitCodeTest(APITestCase):
    """Tests for POST /api/submissions/assignment/<id>/submit/"""

    def setUp(self):
        self.teacher = make_teacher('submit_teacher')
        self.student = make_student('submit_student')
        self.classroom = make_classroom(self.teacher, 'Submit Lab')
        enroll(self.student, self.classroom)
        self.assignment = make_assignment(
            self.classroom, self.teacher, 'Submit Assignment', language='python'
        )
        self.url = reverse('submission-submit', kwargs={'assignment_id': self.assignment.id})

    def test_student_can_submit_code(self):
        """
        An enrolled student can submit code for a published assignment.
        Returns 201 Created with submission details.
        """
        self.client.force_authenticate(user=self.student)
        data = {'source_code': 'print("Hello World")', 'language': 'python'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('submission', response.data)
        self.assertEqual(response.data['submission']['language'], 'python')
        self.assertEqual(response.data['submission']['status'], 'pending')

    def test_submission_saved_in_database(self):
        """After submitting, the submission should exist in the database."""
        self.client.force_authenticate(user=self.student)
        self.client.post(self.url, {'source_code': 'x = 1', 'language': 'python'})
        self.assertTrue(
            Submission.objects.filter(student=self.student, assignment=self.assignment).exists()
        )

    def test_submission_auto_sets_student_and_assignment(self):
        """
        student and assignment must be auto-set from JWT token and URL.
        The student cannot fake who they are or which assignment they target.
        """
        self.client.force_authenticate(user=self.student)
        self.client.post(self.url, {'source_code': 'pass', 'language': 'python'})
        submission = Submission.objects.get(student=self.student)
        self.assertEqual(submission.student, self.student)
        self.assertEqual(submission.assignment, self.assignment)

    def test_submission_starts_as_pending(self):
        """Every new submission must have status='pending'."""
        self.client.force_authenticate(user=self.student)
        self.client.post(self.url, {'source_code': 'pass', 'language': 'python'})
        submission = Submission.objects.get(student=self.student)
        self.assertEqual(submission.status, 'pending')

    def test_student_cannot_submit_to_draft_assignment(self):
        """
        Students cannot submit to assignments that are not yet published.
        Draft assignments return 404 — they don't exist for students.
        """
        draft = make_assignment(self.classroom, self.teacher, 'Draft Assignment', published=False)
        url = reverse('submission-submit', kwargs={'assignment_id': draft.id})
        self.client.force_authenticate(user=self.student)
        response = self.client.post(url, {'source_code': 'pass', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_submit_to_unjoined_classroom_assignment(self):
        """
        A student who hasn't joined the classroom cannot submit.
        Returns 404.
        """
        other_classroom = make_classroom(self.teacher, 'Other Lab')
        other_assignment = make_assignment(other_classroom, self.teacher, 'Other Assignment')
        url = reverse('submission-submit', kwargs={'assignment_id': other_assignment.id})
        self.client.force_authenticate(user=self.student)
        response = self.client.post(url, {'source_code': 'pass', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_can_submit_multiple_times(self):
        """
        A student can resubmit for the same assignment.
        Each submission creates a new record.
        """
        self.client.force_authenticate(user=self.student)
        self.client.post(self.url, {'source_code': 'print("v1")', 'language': 'python'})
        self.client.post(self.url, {'source_code': 'print("v2")', 'language': 'python'})
        count = Submission.objects.filter(
            student=self.student, assignment=self.assignment
        ).count()
        self.assertEqual(count, 2)

    def test_empty_source_code_is_rejected(self):
        """An empty submission should be rejected (400 Bad Request)."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.url, {'source_code': '', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_whitespace_only_source_code_is_rejected(self):
        """Whitespace-only source code should be rejected."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.url, {'source_code': '   \n\t  ', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_language_is_rejected(self):
        """
        Submitting in the wrong language (when assignment specifies one) is rejected.
        The assignment requires Python; submitting Java should fail.
        """
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            self.url, {'source_code': 'System.out.println("hi");', 'language': 'java'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_any_language_accepted_when_assignment_language_is_other(self):
        """
        When the assignment language is 'other', any valid language is accepted.
        """
        assignment = make_assignment(
            self.classroom, self.teacher, 'Open Language Assignment', language='other'
        )
        url = reverse('submission-submit', kwargs={'assignment_id': assignment.id})
        self.client.force_authenticate(user=self.student)
        # Submit with java — should be allowed since assignment is 'other'
        response = self.client.post(url, {'source_code': 'public class A {}', 'language': 'java'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# =============================================================================
# 3. DEADLINE ENFORCEMENT TESTS
# =============================================================================

class DeadlineEnforcementTest(APITestCase):
    """Tests that the submission deadline is properly enforced."""

    def setUp(self):
        self.teacher = make_teacher('deadline_teacher')
        self.student = make_student('deadline_student')
        self.classroom = make_classroom(self.teacher, 'Deadline Lab')
        enroll(self.student, self.classroom)

    def test_submission_allowed_before_deadline(self):
        """
        A submission made before the deadline should succeed.
        """
        future = timezone.now() + timedelta(days=7)
        assignment = make_assignment(
            self.classroom, self.teacher, 'Open Assignment', due_date=future
        )
        url = reverse('submission-submit', kwargs={'assignment_id': assignment.id})
        self.client.force_authenticate(user=self.student)
        response = self.client.post(url, {'source_code': 'pass', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_submission_rejected_after_deadline(self):
        """
        A submission made AFTER the deadline must be rejected (400 Bad Request).
        The error message should mention the deadline.
        """
        # Create assignment with past due_date (deadline already passed)
        past = timezone.now() - timedelta(hours=1)
        assignment = Assignment.objects.create(
            classroom=self.classroom,
            created_by=self.teacher,
            title='Expired Assignment',
            is_published=True,
            due_date=past
        )
        url = reverse('submission-submit', kwargs={'assignment_id': assignment.id})
        self.client.force_authenticate(user=self.student)
        response = self.client.post(url, {'source_code': 'pass', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('deadline', response.data['error'].lower())

    def test_submission_allowed_when_no_due_date(self):
        """
        If there is no deadline, submissions are always accepted.
        """
        assignment = make_assignment(self.classroom, self.teacher, 'No Deadline Assignment')
        # No due_date — should always allow submissions
        url = reverse('submission-submit', kwargs={'assignment_id': assignment.id})
        self.client.force_authenticate(user=self.student)
        response = self.client.post(url, {'source_code': 'pass', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# =============================================================================
# 4. STUDENT: VIEW OWN SUBMISSION HISTORY
# =============================================================================

class MySubmissionListTest(APITestCase):
    """Tests for GET /api/submissions/assignment/<id>/my/"""

    def setUp(self):
        self.teacher = make_teacher('history_teacher')
        self.student = make_student('history_student')
        self.classroom = make_classroom(self.teacher, 'History Lab')
        enroll(self.student, self.classroom)
        self.assignment = make_assignment(self.classroom, self.teacher, 'History Assignment')
        # Create two submissions by this student
        self.s1 = make_submission(self.assignment, self.student, 'print("v1")')
        self.s2 = make_submission(self.assignment, self.student, 'print("v2")')
        self.url = reverse('my-submission-list', kwargs={'assignment_id': self.assignment.id})

    def test_student_sees_own_submissions(self):
        """Student can list their own submission history for an assignment."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_student_does_not_see_other_students_submissions(self):
        """
        A student's history list must NEVER include submissions from other students.
        """
        other_student = make_student('other_history_student')
        enroll(other_student, self.classroom)
        make_submission(self.assignment, other_student, 'print("other")')

        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        # Should still only see 2 (their own), not 3
        self.assertEqual(len(response.data), 2)

    def test_history_list_does_not_include_source_code(self):
        """
        The history list view uses SubmissionListSerializer which does NOT
        include source_code (too heavy for a list). Only the detail view has it.
        """
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        self.assertNotIn('source_code', response.data[0])

    def test_cannot_view_history_of_unjoined_classroom(self):
        """Student cannot view submission history for an assignment in an unjoined classroom."""
        other_classroom = make_classroom(self.teacher, 'Private Lab')
        other_assignment = make_assignment(other_classroom, self.teacher, 'Private Assignment')
        url = reverse('my-submission-list', kwargs={'assignment_id': other_assignment.id})
        self.client.force_authenticate(user=self.student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 5. STUDENT: VIEW ONE SUBMISSION DETAIL
# =============================================================================

class SubmissionDetailTest(APITestCase):
    """Tests for GET /api/submissions/<id>/"""

    def setUp(self):
        self.teacher = make_teacher('detail_teacher')
        self.student = make_student('detail_student')
        self.classroom = make_classroom(self.teacher, 'Detail Lab')
        enroll(self.student, self.classroom)
        self.assignment = make_assignment(self.classroom, self.teacher, 'Detail Assignment')
        self.submission = make_submission(self.assignment, self.student, 'print("detail")')
        self.url = reverse('submission-detail', kwargs={'pk': self.submission.id})

    def test_student_can_view_own_submission_detail(self):
        """Student can view full details of their own submission including source code."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('source_code', response.data)
        self.assertEqual(response.data['source_code'], 'print("detail")')
        self.assertIn('status', response.data)
        self.assertIn('feedback', response.data)

    def test_student_cannot_view_other_students_submission(self):
        """
        CRITICAL SECURITY: A student must NEVER be able to view another
        student's source code, even if they know the submission ID.
        Returns 404 — not even revealing the submission exists.
        """
        other_student = make_student('spy_student')
        enroll(other_student, self.classroom)
        self.client.force_authenticate(user=other_student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_includes_classroom_info(self):
        """Detail view should include classroom_id and classroom_name for context."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        self.assertIn('classroom_id', response.data)
        self.assertIn('classroom_name', response.data)


# =============================================================================
# 6. TEACHER: VIEW ALL SUBMISSIONS
# =============================================================================

class TeacherSubmissionViewTest(APITestCase):
    """Tests for GET /api/submissions/assignment/<id>/all/"""

    def setUp(self):
        self.teacher = make_teacher('view_teacher')
        self.student1 = make_student('view_student1')
        self.student2 = make_student('view_student2')
        self.classroom = make_classroom(self.teacher, 'View Lab')
        enroll(self.student1, self.classroom)
        enroll(self.student2, self.classroom)
        self.assignment = make_assignment(self.classroom, self.teacher, 'View Assignment')
        make_submission(self.assignment, self.student1, 'print("s1")')
        make_submission(self.assignment, self.student2, 'print("s2")')
        self.url = reverse('teacher-submission-list', kwargs={'assignment_id': self.assignment.id})

    def test_teacher_can_view_all_submissions(self):
        """Teacher can view all submissions for their assignment (from all students)."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)   # one from each student

    def test_teacher_submission_list_includes_source_code(self):
        """
        Teacher's view of submissions uses SubmissionDetailSerializer
        which includes source_code — so teachers can review student code.
        """
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertIn('source_code', response.data[0])

    def test_teacher_cannot_view_other_teachers_assignment_submissions(self):
        """
        A teacher cannot see submissions for assignments in another teacher's classroom.
        Returns 404.
        """
        other_teacher = make_teacher('other_view_teacher')
        other_classroom = make_classroom(other_teacher, 'Other View Lab')
        other_student = make_student('other_view_student')
        enroll(other_student, other_classroom)
        other_assignment = make_assignment(other_classroom, other_teacher, 'Other Assignment')
        make_submission(other_assignment, other_student)
        url = reverse('teacher-submission-list', kwargs={'assignment_id': other_assignment.id})

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_access_teacher_view(self):
        """Students cannot access the teacher submission list (403 Forbidden)."""
        self.client.force_authenticate(user=self.student1)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# =============================================================================
# 7. TEACHER: VIEW SPECIFIC STUDENT'S SUBMISSIONS
# =============================================================================

class TeacherStudentSubmissionTest(APITestCase):
    """Tests for GET /api/submissions/assignment/<id>/student/<student_id>/"""

    def setUp(self):
        self.teacher = make_teacher('ts_teacher')
        self.student = make_student('ts_student')
        self.classroom = make_classroom(self.teacher, 'TS Lab')
        enroll(self.student, self.classroom)
        self.assignment = make_assignment(self.classroom, self.teacher, 'TS Assignment')
        make_submission(self.assignment, self.student, 'print("ts1")')
        make_submission(self.assignment, self.student, 'print("ts2")')
        self.url = reverse(
            'teacher-student-submissions',
            kwargs={'assignment_id': self.assignment.id, 'student_id': self.student.id}
        )

    def test_teacher_can_view_specific_student_submissions(self):
        """Teacher can filter submissions by student to see one student's history."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)   # both submissions by this student

    def test_teacher_cannot_view_other_teachers_classroom_specific_student(self):
        """Teacher cannot access another teacher's classroom through this endpoint."""
        other_teacher = make_teacher('other_ts_teacher')
        other_classroom = make_classroom(other_teacher, 'Other TS Lab')
        other_student = make_student('other_ts_student')
        enroll(other_student, other_classroom)
        other_assignment = make_assignment(other_classroom, other_teacher, 'Other TS')
        url = reverse(
            'teacher-student-submissions',
            kwargs={'assignment_id': other_assignment.id, 'student_id': other_student.id}
        )
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 8. SECURITY TESTS
# =============================================================================

class SubmissionSecurityTest(APITestCase):
    """
    Critical security tests — verifying that student data is never exposed
    to other students or unauthorized teachers.
    """

    def setUp(self):
        self.teacher = make_teacher('sec_teacher')
        self.student_a = make_student('sec_student_a')
        self.student_b = make_student('sec_student_b')
        self.classroom = make_classroom(self.teacher, 'Security Lab')
        enroll(self.student_a, self.classroom)
        enroll(self.student_b, self.classroom)
        self.assignment = make_assignment(self.classroom, self.teacher, 'Security Assignment')
        self.submission_a = make_submission(
            self.assignment, self.student_a, 'secret_code_a = True'
        )
        self.submission_b = make_submission(
            self.assignment, self.student_b, 'secret_code_b = True'
        )

    def test_student_b_cannot_see_student_a_submission_detail(self):
        """
        CRITICAL: Student B must not be able to read Student A's source code
        by directly accessing the submission ID.
        """
        url = reverse('submission-detail', kwargs={'pk': self.submission_a.id})
        self.client.force_authenticate(user=self.student_b)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_b_cannot_see_student_a_history(self):
        """
        Student B's submission history list must never contain Student A's submissions.
        """
        url = reverse('my-submission-list', kwargs={'assignment_id': self.assignment.id})
        self.client.force_authenticate(user=self.student_b)
        response = self.client.get(url)
        # Student B only has 1 submission — should see only their own
        self.assertEqual(len(response.data), 1)
        # Verify the returned submission belongs to student_b
        self.assertEqual(response.data[0]['id'], self.submission_b.id)

    def test_source_code_not_exposed_in_list_view(self):
        """
        Even in a teacher's list view, source_code should be in the detail serializer.
        In student's own list view, source_code is NOT included (compact serializer).
        """
        url = reverse('my-submission-list', kwargs={'assignment_id': self.assignment.id})
        self.client.force_authenticate(user=self.student_a)
        response = self.client.get(url)
        # List view uses SubmissionListSerializer — no source_code field
        self.assertNotIn('source_code', response.data[0])


# =============================================================================
# 9. PERMISSION TESTS
# =============================================================================

class SubmissionPermissionTest(APITestCase):
    """
    Tests that role-based permissions work correctly.
    Every endpoint should block:
      - Unauthenticated users → 401
      - Wrong role → 403
      - Pending teachers → 403
    """

    def setUp(self):
        self.teacher = make_teacher('perm_teacher')
        self.student = make_student('perm_student')
        self.pending = make_teacher('perm_pending', approved=False)
        self.classroom = make_classroom(self.teacher, 'Permission Lab')
        enroll(self.student, self.classroom)
        self.assignment = make_assignment(self.classroom, self.teacher, 'Permission Assignment')
        self.submission = make_submission(self.assignment, self.student)

    def test_unauthenticated_cannot_submit(self):
        """Unauthenticated user cannot submit code (401)."""
        url = reverse('submission-submit', kwargs={'assignment_id': self.assignment.id})
        response = self.client.post(url, {'source_code': 'pass', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_cannot_submit_code(self):
        """Teachers cannot submit code — that's a student action (403)."""
        url = reverse('submission-submit', kwargs={'assignment_id': self.assignment.id})
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(url, {'source_code': 'pass', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_teacher_cannot_submit(self):
        """Pending (unapproved) teacher cannot submit code (403)."""
        url = reverse('submission-submit', kwargs={'assignment_id': self.assignment.id})
        self.client.force_authenticate(user=self.pending)
        response = self.client.post(url, {'source_code': 'pass', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_view_submissions(self):
        """Unauthenticated user cannot view submission history (401)."""
        url = reverse('my-submission-list', kwargs={'assignment_id': self.assignment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_cannot_access_student_history_endpoint(self):
        """Teachers cannot use the student-only /my/ endpoint (403)."""
        url = reverse('my-submission-list', kwargs={'assignment_id': self.assignment.id})
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_access_teacher_all_submissions(self):
        """Students cannot access the teacher-only /all/ endpoint (403)."""
        url = reverse('teacher-submission-list', kwargs={'assignment_id': self.assignment.id})
        self.client.force_authenticate(user=self.student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_teacher_cannot_view_submissions(self):
        """Pending teacher cannot view submission list (403)."""
        url = reverse('teacher-submission-list', kwargs={'assignment_id': self.assignment.id})
        self.client.force_authenticate(user=self.pending)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_view_teacher_submissions(self):
        """Unauthenticated user cannot access teacher endpoints (401)."""
        url = reverse('teacher-submission-list', kwargs={'assignment_id': self.assignment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
