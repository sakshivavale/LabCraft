"""
assignments/tests.py

Tests for the Assignment Management module.

Run these tests with:
  cd backend
  python manage.py test assignments -v 2

Run ALL module tests together with:
  python manage.py test accounts classrooms assignments -v 2

Test classes:
  1. AssignmentModelTest            — model fields, is_past_due, status, __str__
  2. TeacherAssignmentCreateTest    — POST creates assignment with correct data
  3. TeacherAssignmentListTest      — GET lists teacher's assignments
  4. TeacherAssignmentCRUDTest      — PATCH, DELETE, 404 on other teacher's assignment
  5. StudentAssignmentListTest      — students see only published in joined classrooms
  6. StudentAssignmentDetailTest    — student view one assignment, access control
  7. AssignmentValidationTest       — input validation (blank title, marks, due_date)
  8. AssignmentPermissionTest       — role-based access, unauthenticated, wrong role
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from classrooms.models import Classroom, ClassroomMembership
from .models import Assignment

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

def make_assignment(classroom, teacher, title='Test Assignment', **kwargs):
    """
    Create an assignment in the given classroom by the given teacher.
    Extra kwargs (like is_published=True, due_date=...) can be passed in.
    """
    return Assignment.objects.create(
        classroom=classroom,
        created_by=teacher,
        title=title,
        **kwargs
    )


# =============================================================================
# 1. MODEL TESTS
# =============================================================================

class AssignmentModelTest(TestCase):
    """Tests for the Assignment model's fields, properties, and string representation."""

    def setUp(self):
        """Set up a teacher and classroom used by all tests in this class."""
        self.teacher = make_teacher('model_teacher')
        self.classroom = make_classroom(self.teacher, 'Python Lab')

    def test_assignment_created_with_correct_defaults(self):
        """
        Creating an assignment should auto-set default values:
        is_published=False, difficulty='medium', language='python', max_marks=100.
        """
        assignment = make_assignment(self.classroom, self.teacher, 'Lab 1')
        self.assertEqual(assignment.title, 'Lab 1')
        self.assertEqual(assignment.classroom, self.classroom)
        self.assertEqual(assignment.created_by, self.teacher)
        self.assertFalse(assignment.is_published)         # draft by default
        self.assertEqual(assignment.language, 'python')   # default language
        self.assertEqual(assignment.difficulty, 'medium') # default difficulty
        self.assertEqual(assignment.max_marks, 100)       # default max marks
        self.assertEqual(assignment.description, '')      # blank by default
        self.assertEqual(assignment.instructions, '')     # blank by default
        self.assertIsNone(assignment.due_date)            # no deadline by default

    def test_str_returns_title_and_classroom_name(self):
        """__str__ should return 'title (classroom_name)'."""
        assignment = make_assignment(self.classroom, self.teacher, 'Lab 1')
        self.assertEqual(str(assignment), 'Lab 1 (Python Lab)')

    def test_is_past_due_false_when_no_due_date(self):
        """
        If no due_date is set, is_past_due must return False.
        An assignment with no deadline never expires.
        """
        assignment = make_assignment(self.classroom, self.teacher)
        self.assertFalse(assignment.is_past_due)

    def test_is_past_due_false_when_future_due_date(self):
        """is_past_due must return False if the deadline is in the future."""
        future = timezone.now() + timedelta(days=7)
        assignment = make_assignment(self.classroom, self.teacher, due_date=future)
        self.assertFalse(assignment.is_past_due)

    def test_is_past_due_true_when_past_due_date(self):
        """is_past_due must return True if the deadline has already passed."""
        past = timezone.now() - timedelta(days=1)
        assignment = make_assignment(self.classroom, self.teacher, due_date=past)
        self.assertTrue(assignment.is_past_due)

    def test_status_draft_when_not_published(self):
        """status must be 'draft' when is_published=False, regardless of due_date."""
        assignment = make_assignment(self.classroom, self.teacher, is_published=False)
        self.assertEqual(assignment.status, 'draft')

    def test_status_open_when_published_and_not_past_due(self):
        """status must be 'open' when published and deadline hasn't passed."""
        future = timezone.now() + timedelta(days=5)
        assignment = make_assignment(
            self.classroom, self.teacher, is_published=True, due_date=future
        )
        self.assertEqual(assignment.status, 'open')

    def test_status_closed_when_published_and_past_due(self):
        """status must be 'closed' when published but deadline has passed."""
        past = timezone.now() - timedelta(days=1)
        assignment = make_assignment(
            self.classroom, self.teacher, is_published=True, due_date=past
        )
        self.assertEqual(assignment.status, 'closed')

    def test_status_open_when_published_with_no_due_date(self):
        """status is 'open' when published and no due_date — no deadline means always open."""
        assignment = make_assignment(self.classroom, self.teacher, is_published=True)
        self.assertEqual(assignment.status, 'open')

    def test_ordering_newest_first(self):
        """Assignments should be ordered with the newest first (Meta.ordering = ['-created_at'])."""
        a1 = make_assignment(self.classroom, self.teacher, 'First')
        a2 = make_assignment(self.classroom, self.teacher, 'Second')
        assignments = list(Assignment.objects.all())
        # Second was created after First, so it should appear first
        self.assertEqual(assignments[0], a2)
        self.assertEqual(assignments[1], a1)


# =============================================================================
# 2. TEACHER: CREATE ASSIGNMENT TESTS
# =============================================================================

class TeacherAssignmentCreateTest(APITestCase):
    """Tests for POST /api/assignments/classroom/<id>/"""

    def setUp(self):
        self.teacher = make_teacher('create_teacher')
        self.classroom = make_classroom(self.teacher, 'Java Lab')
        self.url = reverse('assignment-list-create', kwargs={'classroom_id': self.classroom.id})

    def test_teacher_can_create_assignment(self):
        """
        An approved teacher should be able to create an assignment in their classroom.
        Returns 201 Created with assignment details.
        """
        self.client.force_authenticate(user=self.teacher)
        data = {
            'title': 'Lab 1: Hello World',
            'description': 'Write your first Java program.',
            'language': 'java',
            'difficulty': 'easy',
            'max_marks': 50,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('assignment', response.data)
        self.assertEqual(response.data['assignment']['title'], 'Lab 1: Hello World')
        # classroom and created_by must be auto-set, NOT from request body
        self.assertEqual(response.data['assignment']['classroom_id'], self.classroom.id)
        self.assertEqual(response.data['assignment']['created_by']['id'], self.teacher.id)

    def test_assignment_saved_in_database(self):
        """After creating, the assignment should actually exist in the database."""
        self.client.force_authenticate(user=self.teacher)
        self.client.post(self.url, {'title': 'DB Test Lab', 'language': 'python'})
        self.assertTrue(Assignment.objects.filter(title='DB Test Lab').exists())

    def test_assignment_starts_as_draft(self):
        """
        is_published should default to False — the teacher must explicitly publish.
        Students shouldn't see assignments the moment they're created.
        """
        self.client.force_authenticate(user=self.teacher)
        self.client.post(self.url, {'title': 'Draft Lab', 'language': 'python'})
        assignment = Assignment.objects.get(title='Draft Lab')
        self.assertFalse(assignment.is_published)

    def test_teacher_can_create_published_assignment(self):
        """Teacher can pass is_published=True to publish immediately."""
        self.client.force_authenticate(user=self.teacher)
        data = {'title': 'Published Lab', 'language': 'python', 'is_published': True}
        self.client.post(self.url, data)
        assignment = Assignment.objects.get(title='Published Lab')
        self.assertTrue(assignment.is_published)

    def test_teacher_cannot_create_in_other_teachers_classroom(self):
        """
        A teacher should NOT be able to create assignments in another teacher's classroom.
        Returns 404 — we don't reveal the classroom exists.
        """
        other_teacher = make_teacher('other_teacher')
        other_classroom = make_classroom(other_teacher, 'Other Lab')
        url = reverse('assignment-list-create', kwargs={'classroom_id': other_classroom.id})

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(url, {'title': 'Hacked Lab', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pending_teacher_cannot_create_assignment(self):
        """A teacher who is NOT yet approved should be blocked (403 Forbidden)."""
        pending = make_teacher('pending_teacher', approved=False)
        self.client.force_authenticate(user=pending)
        response = self.client.post(self.url, {'title': 'Hacked', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_create_assignment(self):
        """Students must not be able to create assignments (403 Forbidden)."""
        student = make_student('student_creator')
        self.client.force_authenticate(user=student)
        response = self.client.post(self.url, {'title': 'Student Lab', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_assignment(self):
        """Unauthenticated requests must be rejected (401 Unauthorized)."""
        response = self.client.post(self.url, {'title': 'Anon Lab', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# 3. TEACHER: LIST ASSIGNMENTS TESTS
# =============================================================================

class TeacherAssignmentListTest(APITestCase):
    """Tests for GET /api/assignments/classroom/<id>/"""

    def setUp(self):
        self.teacher = make_teacher('list_teacher')
        self.classroom = make_classroom(self.teacher, 'List Lab')
        self.url = reverse('assignment-list-create', kwargs={'classroom_id': self.classroom.id})
        # Create two assignments — one draft, one published
        self.draft = make_assignment(self.classroom, self.teacher, 'Draft Lab', is_published=False)
        self.published = make_assignment(self.classroom, self.teacher, 'Published Lab', is_published=True)

    def test_teacher_can_list_all_assignments_including_drafts(self):
        """
        Teacher should see BOTH draft and published assignments.
        Students can't see drafts, but the teacher who wrote them can.
        """
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [a['title'] for a in response.data]
        self.assertIn('Draft Lab', titles)
        self.assertIn('Published Lab', titles)

    def test_teacher_does_not_see_other_classroom_assignments(self):
        """Teacher should only see assignments in the requested classroom."""
        other_classroom = make_classroom(self.teacher, 'Other Classroom')
        make_assignment(other_classroom, self.teacher, 'Other Lab')

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        titles = [a['title'] for a in response.data]
        self.assertNotIn('Other Lab', titles)   # from different classroom

    def test_teacher_cannot_list_other_teachers_classroom(self):
        """
        Trying to list assignments in another teacher's classroom returns 404.
        The filtered queryset is empty → 404, not 403.
        """
        other_teacher = make_teacher('other_list_teacher')
        other_classroom = make_classroom(other_teacher, 'Secret Lab')
        url = reverse('assignment-list-create', kwargs={'classroom_id': other_classroom.id})

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(url)
        # Empty queryset → returns empty list, but actually classroom_id filter
        # means no assignments owned by this teacher appear. 200 with empty list.
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(len(response.data), 0)


# =============================================================================
# 4. TEACHER: CRUD (GET / PATCH / DELETE) SPECIFIC ASSIGNMENT
# =============================================================================

class TeacherAssignmentCRUDTest(APITestCase):
    """Tests for GET/PATCH/DELETE /api/assignments/<id>/"""

    def setUp(self):
        self.teacher = make_teacher('crud_teacher')
        self.classroom = make_classroom(self.teacher, 'CRUD Lab')
        self.assignment = make_assignment(
            self.classroom, self.teacher, 'CRUD Test Lab',
            description='Original description'
        )
        self.url = reverse('assignment-detail', kwargs={'pk': self.assignment.id})

    def test_teacher_can_view_assignment_detail(self):
        """Teacher can GET a specific assignment and see full details including instructions."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'CRUD Test Lab')
        # Detail view includes instructions field (not in list view)
        self.assertIn('instructions', response.data)

    def test_teacher_can_patch_assignment(self):
        """Teacher can partially update (PATCH) their assignment."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.patch(self.url, {'title': 'Updated Lab Title'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        # Verify the update was saved
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.title, 'Updated Lab Title')

    def test_teacher_can_publish_assignment_via_patch(self):
        """Teacher can publish a draft assignment by PATCHing is_published=True."""
        self.client.force_authenticate(user=self.teacher)
        self.assertFalse(self.assignment.is_published)   # starts as draft
        self.client.patch(self.url, {'is_published': True})
        self.assignment.refresh_from_db()
        self.assertTrue(self.assignment.is_published)

    def test_teacher_can_delete_assignment(self):
        """Teacher can delete their assignment. Returns 200 with a message."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        # Verify it was actually deleted from the database
        self.assertFalse(Assignment.objects.filter(id=self.assignment.id).exists())

    def test_teacher_cannot_access_other_teachers_assignment(self):
        """
        A teacher trying to GET/PATCH/DELETE another teacher's assignment gets 404.
        get_queryset() filters by created_by=request.user, so other teachers' assignments
        don't appear → 404 (not revealing the assignment exists).
        """
        other_teacher = make_teacher('other_crud_teacher')
        other_classroom = make_classroom(other_teacher, 'Other CRUD Lab')
        other_assignment = make_assignment(other_classroom, other_teacher, 'Other Assignment')
        url = reverse('assignment-detail', kwargs={'pk': other_assignment.id})

        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.patch(url, {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 5. STUDENT: LIST ASSIGNMENTS TESTS
# =============================================================================

class StudentAssignmentListTest(APITestCase):
    """Tests for GET /api/assignments/classroom/<id>/student/"""

    def setUp(self):
        self.teacher = make_teacher('student_list_teacher')
        self.student = make_student('student_lister')
        self.classroom = make_classroom(self.teacher, 'Student List Lab')
        # Student joins the classroom
        ClassroomMembership.objects.create(student=self.student, classroom=self.classroom)
        # Create assignments: one draft, one published
        self.draft = make_assignment(self.classroom, self.teacher, 'Draft Lab', is_published=False)
        self.published = make_assignment(
            self.classroom, self.teacher, 'Published Lab', is_published=True
        )
        self.url = reverse(
            'student-assignment-list', kwargs={'classroom_id': self.classroom.id}
        )

    def test_student_sees_published_assignments_in_joined_classroom(self):
        """Students must see published assignments in classrooms they've joined."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [a['title'] for a in response.data]
        self.assertIn('Published Lab', titles)

    def test_student_does_not_see_draft_assignments(self):
        """
        Students must NEVER see draft assignments (is_published=False).
        Only the teacher sees drafts.
        """
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        titles = [a['title'] for a in response.data]
        self.assertNotIn('Draft Lab', titles)

    def test_student_cannot_access_unjoined_classroom_assignments(self):
        """
        A student who hasn't joined a classroom should get 404 when trying
        to list that classroom's assignments. We don't reveal the classroom exists.
        """
        other_classroom = make_classroom(self.teacher, 'Private Lab')
        make_assignment(other_classroom, self.teacher, 'Private Assignment', is_published=True)
        url = reverse('student-assignment-list', kwargs={'classroom_id': other_classroom.id})

        self.client.force_authenticate(user=self.student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_access_student_endpoint(self):
        """Teachers cannot use the student-only endpoint (403 Forbidden)."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_student_assignments(self):
        """Unauthenticated requests are rejected (401 Unauthorized)."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# 6. STUDENT: VIEW SPECIFIC ASSIGNMENT TESTS
# =============================================================================

class StudentAssignmentDetailTest(APITestCase):
    """Tests for GET /api/assignments/<id>/student/"""

    def setUp(self):
        self.teacher = make_teacher('detail_teacher')
        self.student = make_student('detail_student')
        self.classroom = make_classroom(self.teacher, 'Detail Lab')
        # Student joins the classroom
        ClassroomMembership.objects.create(student=self.student, classroom=self.classroom)
        # Published assignment in joined classroom
        self.published = make_assignment(
            self.classroom, self.teacher, 'Published Detail Lab', is_published=True
        )
        # Draft assignment (student should NOT see it)
        self.draft = make_assignment(
            self.classroom, self.teacher, 'Draft Detail Lab', is_published=False
        )
        self.published_url = reverse(
            'student-assignment-detail', kwargs={'pk': self.published.id}
        )
        self.draft_url = reverse(
            'student-assignment-detail', kwargs={'pk': self.draft.id}
        )

    def test_student_can_view_published_assignment_detail(self):
        """
        Student can view full details of a published assignment in their classroom.
        The detail view includes instructions (not shown in list view).
        """
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.published_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Published Detail Lab')
        self.assertIn('instructions', response.data)

    def test_student_cannot_view_draft_assignment(self):
        """
        Student must NOT be able to view draft (unpublished) assignments.
        Returns 404 — the draft simply doesn't exist for the student.
        """
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.draft_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_view_assignment_in_unjoined_classroom(self):
        """
        A student who hasn't joined a classroom cannot view its assignments
        even if they somehow know the assignment ID.
        """
        other_classroom = make_classroom(self.teacher, 'Other Detail Lab')
        # Student is NOT a member of other_classroom
        other_assignment = make_assignment(
            other_classroom, self.teacher, 'Other Assignment', is_published=True
        )
        url = reverse('student-assignment-detail', kwargs={'pk': other_assignment.id})

        self.client.force_authenticate(user=self.student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 7. INPUT VALIDATION TESTS
# =============================================================================

class AssignmentValidationTest(APITestCase):
    """Tests for input validation in AssignmentWriteSerializer."""

    def setUp(self):
        self.teacher = make_teacher('validation_teacher')
        self.classroom = make_classroom(self.teacher, 'Validation Lab')
        self.url = reverse('assignment-list-create', kwargs={'classroom_id': self.classroom.id})
        self.client.force_authenticate(user=self.teacher)

    def test_blank_title_is_rejected(self):
        """
        An assignment with an empty title must be rejected (400 Bad Request).
        A blank title like '' or '   ' is meaningless.
        """
        response = self.client.post(self.url, {'title': '', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_whitespace_only_title_is_rejected(self):
        """A title that is only whitespace should be rejected after strip()."""
        response = self.client.post(self.url, {'title': '   ', 'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_title_is_required(self):
        """Title field is required. Missing it should return 400."""
        response = self.client.post(self.url, {'language': 'python'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_max_marks_is_rejected(self):
        """
        max_marks must be at least 1. Zero is meaningless.
        Our serializer validate_max_marks() catches this.
        """
        response = self.client.post(
            self.url, {'title': 'Zero Marks Lab', 'language': 'python', 'max_marks': 0}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_language_choice_is_rejected(self):
        """Language must be one of the defined TextChoices. Random strings are rejected."""
        response = self.client.post(
            self.url, {'title': 'Bad Lang Lab', 'language': 'brainfuck'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_difficulty_choice_is_rejected(self):
        """Difficulty must be 'easy', 'medium', or 'hard'. Other values are rejected."""
        response = self.client.post(
            self.url, {'title': 'Bad Diff Lab', 'language': 'python', 'difficulty': 'extreme'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_past_due_date_on_create_is_rejected(self):
        """
        When CREATING an assignment, the due_date must be in the future.
        A past due_date means the assignment is already expired before students see it.
        """
        past = (timezone.now() - timedelta(days=1)).isoformat()
        response = self.client.post(
            self.url,
            {'title': 'Expired Lab', 'language': 'python', 'due_date': past}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_future_due_date_on_create_is_accepted(self):
        """A future due_date on create is valid and should return 201."""
        future = (timezone.now() + timedelta(days=7)).isoformat()
        response = self.client.post(
            self.url,
            {'title': 'Future Lab', 'language': 'python', 'due_date': future}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_past_due_date_on_update_is_allowed(self):
        """
        When UPDATING an assignment, we allow setting a past due_date.
        WHY? Teachers may need to keep historical records or close an assignment retroactively.
        """
        assignment = make_assignment(self.classroom, self.teacher, 'Update Due Date Lab')
        url = reverse('assignment-detail', kwargs={'pk': assignment.id})
        past = (timezone.now() - timedelta(days=1)).isoformat()
        response = self.client.patch(url, {'due_date': past})
        # Should succeed (200), not fail (400)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_valid_assignment_creation_returns_201(self):
        """A fully valid assignment should be created successfully."""
        future = (timezone.now() + timedelta(days=14)).isoformat()
        data = {
            'title': 'Complete Lab',
            'description': 'A complete test lab.',
            'instructions': 'Step 1: ...',
            'due_date': future,
            'max_marks': 75,
            'language': 'java',
            'difficulty': 'hard',
            'is_published': False,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# =============================================================================
# 8. PERMISSION TESTS
# =============================================================================

class AssignmentPermissionTest(APITestCase):
    """
    Tests that role-based permissions work correctly across all endpoints.
    Every endpoint should block:
      - Unauthenticated users → 401
      - Wrong role → 403
      - Pending teachers → 403
    """

    def setUp(self):
        self.teacher = make_teacher('perm_teacher')
        self.student = make_student('perm_student')
        self.pending = make_teacher('pending_perm_teacher', approved=False)
        self.classroom = make_classroom(self.teacher, 'Permission Lab')
        ClassroomMembership.objects.create(student=self.student, classroom=self.classroom)
        self.assignment = make_assignment(
            self.classroom, self.teacher, 'Perm Lab', is_published=True
        )

    def test_teacher_endpoint_blocks_unauthenticated(self):
        """Unauthenticated user cannot create or list teacher assignments."""
        url = reverse('assignment-list-create', kwargs={'classroom_id': self.classroom.id})
        self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(url, {}).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_endpoint_blocks_unauthenticated(self):
        """Unauthenticated user cannot access student assignment endpoints."""
        url = reverse('student-assignment-list', kwargs={'classroom_id': self.classroom.id})
        self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_endpoints_block_students(self):
        """
        Students cannot access teacher endpoints (list/create/update/delete).
        Returns 403 Forbidden because they are authenticated but wrong role.
        """
        self.client.force_authenticate(user=self.student)
        url = reverse('assignment-list-create', kwargs={'classroom_id': self.classroom.id})
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(url, {}).status_code, status.HTTP_403_FORBIDDEN)

        detail_url = reverse('assignment-detail', kwargs={'pk': self.assignment.id})
        self.assertEqual(self.client.patch(detail_url, {}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_403_FORBIDDEN)

    def test_student_endpoints_block_teachers(self):
        """
        Teachers cannot access student-only endpoints.
        Returns 403 Forbidden.
        """
        self.client.force_authenticate(user=self.teacher)
        url = reverse('student-assignment-list', kwargs={'classroom_id': self.classroom.id})
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

        detail_url = reverse('student-assignment-detail', kwargs={'pk': self.assignment.id})
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_teacher_cannot_access_teacher_endpoints(self):
        """
        A teacher whose account is not yet approved (is_approved=False)
        is blocked from all teacher endpoints (403 Forbidden).
        """
        self.client.force_authenticate(user=self.pending)
        url = reverse('assignment-list-create', kwargs={'classroom_id': self.classroom.id})
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(url, {}).status_code, status.HTTP_403_FORBIDDEN)
