"""
classrooms/tests.py

Tests for the Classroom Management module.

Run these tests with:
  cd backend
  python manage.py test classrooms -v 2

Test classes:
  1. ClassroomModelTest          — model fields, join_code generation, uniqueness
  2. TeacherClassroomCRUDTest    — teacher create/read/update/delete classrooms
  3. JoinCodeTest                — join code generation, uniqueness, format
  4. StudentJoinClassroomTest    — join, duplicate prevention, inactive classrooms
  5. StudentClassroomViewTest    — viewing joined classrooms
  6. StudentLeaveClassroomTest   — leaving a classroom
  7. TeacherStudentListTest      — teacher views their classroom's students
  8. PermissionTest              — role-based access enforcement
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from .models import Classroom, ClassroomMembership

User = get_user_model()


# =============================================================================
# HELPER: create test users easily
# =============================================================================

def make_student(username, email=None, password='StrongPass123!'):
    return User.objects.create_user(
        username=username,
        email=email or f'{username}@test.com',
        password=password,
        role=User.Role.STUDENT,
        is_approved=True,
    )

def make_teacher(username, email=None, password='StrongPass123!', approved=True):
    return User.objects.create_user(
        username=username,
        email=email or f'{username}@test.com',
        password=password,
        role=User.Role.TEACHER,
        is_approved=approved,
    )


# =============================================================================
# 1. MODEL TESTS
# =============================================================================

class ClassroomModelTest(TestCase):
    """Tests for the Classroom and ClassroomMembership models."""

    def setUp(self):
        self.teacher = make_teacher('model_teacher')

    def test_classroom_created_with_correct_fields(self):
        """Creating a classroom should set name, teacher, and defaults."""
        classroom = Classroom.objects.create(
            teacher=self.teacher,
            name='Test Classroom',
        )
        self.assertEqual(classroom.name, 'Test Classroom')
        self.assertEqual(classroom.teacher, self.teacher)
        self.assertTrue(classroom.is_active)   # default
        self.assertEqual(classroom.description, '')  # default

    def test_join_code_auto_generated_on_save(self):
        """
        join_code must be generated automatically when classroom is saved.
        No code should be provided by the teacher — it's auto-created.
        """
        classroom = Classroom.objects.create(
            teacher=self.teacher, name='Auto Code Room'
        )
        self.assertTrue(bool(classroom.join_code))    # not empty
        self.assertEqual(len(classroom.join_code), 8) # exactly 8 characters
        # Join code is uppercase hex — all alphabetic characters must be uppercase.
        # We use upper() comparison instead of isupper() because isupper() returns
        # False when the string has no letters at all (e.g. a purely numeric code
        # like '12345678'), which is a valid UUID hex slice.
        self.assertEqual(classroom.join_code, classroom.join_code.upper())

    def test_join_code_is_unique_across_classrooms(self):
        """Every classroom must have a different join code."""
        c1 = Classroom.objects.create(teacher=self.teacher, name='Room 1')
        c2 = Classroom.objects.create(teacher=self.teacher, name='Room 2')
        self.assertNotEqual(c1.join_code, c2.join_code)

    def test_join_code_not_regenerated_on_update(self):
        """Saving an existing classroom should NOT change its join_code."""
        classroom = Classroom.objects.create(teacher=self.teacher, name='Stable Room')
        original_code = classroom.join_code
        classroom.name = 'Renamed Room'
        classroom.save()
        classroom.refresh_from_db()
        self.assertEqual(classroom.join_code, original_code)  # code unchanged

    def test_student_count_property(self):
        """student_count should return the correct number of students."""
        classroom = Classroom.objects.create(teacher=self.teacher, name='Count Room')
        s1 = make_student('count_student1')
        s2 = make_student('count_student2')
        ClassroomMembership.objects.create(student=s1, classroom=classroom)
        ClassroomMembership.objects.create(student=s2, classroom=classroom)
        self.assertEqual(classroom.student_count, 2)

    def test_str_method(self):
        """__str__ should return 'name (by teacher_username)'."""
        classroom = Classroom.objects.create(teacher=self.teacher, name='My Lab')
        self.assertIn('My Lab', str(classroom))
        self.assertIn(self.teacher.username, str(classroom))

    def test_classroom_membership_uniqueness_constraint(self):
        """A student cannot join the same classroom twice at the DB level."""
        from django.db import IntegrityError
        classroom = Classroom.objects.create(teacher=self.teacher, name='Unique Room')
        student = make_student('unique_student')
        ClassroomMembership.objects.create(student=student, classroom=classroom)
        with self.assertRaises(IntegrityError):
            ClassroomMembership.objects.create(student=student, classroom=classroom)

    def test_membership_str_method(self):
        """ClassroomMembership __str__ should name student and classroom."""
        classroom = Classroom.objects.create(teacher=self.teacher, name='Str Room')
        student = make_student('str_student')
        m = ClassroomMembership.objects.create(student=student, classroom=classroom)
        self.assertIn(student.username, str(m))
        self.assertIn(classroom.name, str(m))


# =============================================================================
# 2. TEACHER CLASSROOM CRUD TESTS
# =============================================================================

class TeacherClassroomCRUDTest(APITestCase):
    """Tests for teacher create/read/update/delete classroom endpoints."""

    def setUp(self):
        self.teacher = make_teacher('crud_teacher')
        self.other_teacher = make_teacher('other_teacher')
        self.client.force_authenticate(user=self.teacher)
        self.list_url = reverse('classroom-list-create')

    def test_teacher_can_create_classroom(self):
        """POST /api/classrooms/ with valid data should return 201."""
        response = self.client.post(
            self.list_url,
            {'name': 'New Classroom', 'description': 'A test room'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('join_code', response.data)
        self.assertEqual(response.data['classroom']['teacher']['username'], 'crud_teacher')

    def test_created_classroom_belongs_to_teacher(self):
        """The classroom's teacher must be the logged-in teacher."""
        self.client.post(self.list_url, {'name': 'My Room'}, format='json')
        classroom = Classroom.objects.get(name='My Room')
        self.assertEqual(classroom.teacher, self.teacher)

    def test_teacher_lists_only_own_classrooms(self):
        """Teacher should only see their own classrooms, not other teachers'."""
        Classroom.objects.create(teacher=self.teacher, name='Mine')
        Classroom.objects.create(teacher=self.other_teacher, name='Theirs')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Mine')

    def test_teacher_can_update_classroom(self):
        """PATCH /api/classrooms/<id>/ should update the classroom name."""
        classroom = Classroom.objects.create(teacher=self.teacher, name='Old Name')
        url = reverse('classroom-detail', kwargs={'pk': classroom.pk})
        response = self.client.patch(url, {'name': 'New Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        classroom.refresh_from_db()
        self.assertEqual(classroom.name, 'New Name')

    def test_teacher_cannot_update_another_teachers_classroom(self):
        """
        SECURITY: teacher should get 404 (not 403) when targeting
        another teacher's classroom — the classroom isn't even visible to them.
        """
        classroom = Classroom.objects.create(teacher=self.other_teacher, name='Theirs')
        url = reverse('classroom-detail', kwargs={'pk': classroom.pk})
        response = self.client.patch(url, {'name': 'Stolen Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_can_delete_classroom(self):
        """DELETE /api/classrooms/<id>/ should remove the classroom."""
        classroom = Classroom.objects.create(teacher=self.teacher, name='To Delete')
        url = reverse('classroom-detail', kwargs={'pk': classroom.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Classroom.objects.filter(pk=classroom.pk).exists())

    def test_blank_name_returns_400(self):
        """Classroom name cannot be blank."""
        response = self.client.post(self.list_url, {'name': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# 3. STUDENT JOIN CLASSROOM TESTS
# =============================================================================

class StudentJoinClassroomTest(APITestCase):
    """Tests for the join classroom endpoint."""

    def setUp(self):
        self.teacher = make_teacher('join_teacher')
        self.student = make_student('join_student')
        self.classroom = Classroom.objects.create(teacher=self.teacher, name='Join Room')
        self.url = reverse('classroom-join')
        self.client.force_authenticate(user=self.student)

    def test_student_can_join_with_valid_code(self):
        """POST /api/classrooms/join/ with valid code should create membership."""
        response = self.client.post(
            self.url, {'join_code': self.classroom.join_code}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('joined', response.data['message'].lower())
        self.assertTrue(
            ClassroomMembership.objects.filter(
                student=self.student, classroom=self.classroom
            ).exists()
        )

    def test_student_cannot_join_twice(self):
        """
        CRITICAL: joining the same classroom twice must be blocked.
        First join succeeds; second returns 400.
        """
        self.client.post(self.url, {'join_code': self.classroom.join_code}, format='json')
        response = self.client.post(
            self.url, {'join_code': self.classroom.join_code}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already', response.data['error'].lower())

    def test_invalid_join_code_returns_400(self):
        """Wrong code should return 400 with a clear error."""
        response = self.client.post(self.url, {'join_code': 'XXXXXXXX'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_join_inactive_classroom(self):
        """An inactive classroom should not accept new students."""
        self.classroom.is_active = False
        self.classroom.save()
        response = self.client.post(
            self.url, {'join_code': self.classroom.join_code}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('active', response.data['join_code'][0].lower())

    def test_teacher_cannot_join_classroom(self):
        """Teachers should not be able to use the join endpoint (403)."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self.url, {'join_code': self.classroom.join_code}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_join_code_case_insensitive(self):
        """
        Join code validation normalizes to uppercase,
        so lowercase input should also work.
        """
        lowercase_code = self.classroom.join_code.lower()
        response = self.client.post(self.url, {'join_code': lowercase_code}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# =============================================================================
# 4. STUDENT VIEW / LEAVE CLASSROOM TESTS
# =============================================================================

class StudentClassroomViewTest(APITestCase):
    """Tests for student viewing joined classrooms."""

    def setUp(self):
        self.teacher = make_teacher('view_teacher')
        self.student = make_student('view_student')
        self.client.force_authenticate(user=self.student)
        self.room1 = Classroom.objects.create(teacher=self.teacher, name='Room 1')
        self.room2 = Classroom.objects.create(teacher=self.teacher, name='Room 2')
        # Join room1 only
        ClassroomMembership.objects.create(student=self.student, classroom=self.room1)

    def test_student_sees_only_joined_classrooms(self):
        """GET /api/classrooms/my/ should only return rooms the student joined."""
        url = reverse('my-classrooms')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Room 1')

    def test_student_can_view_joined_classroom_detail(self):
        """Student can view details of a classroom they are a member of."""
        url = reverse('classroom-detail-student', kwargs={'pk': self.room1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Room 1')

    def test_student_cannot_view_non_joined_classroom_detail(self):
        """Student cannot view details of a classroom they haven't joined."""
        url = reverse('classroom-detail-student', kwargs={'pk': self.room2.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class StudentLeaveClassroomTest(APITestCase):
    """Tests for the leave classroom endpoint."""

    def setUp(self):
        self.teacher = make_teacher('leave_teacher')
        self.student = make_student('leave_student')
        self.classroom = Classroom.objects.create(teacher=self.teacher, name='Leave Room')
        self.membership = ClassroomMembership.objects.create(
            student=self.student, classroom=self.classroom
        )
        self.client.force_authenticate(user=self.student)

    def test_student_can_leave_classroom(self):
        """DELETE /api/classrooms/<id>/leave/ should remove the membership."""
        url = reverse('classroom-leave', kwargs={'pk': self.classroom.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            ClassroomMembership.objects.filter(
                student=self.student, classroom=self.classroom
            ).exists()
        )

    def test_student_cannot_leave_classroom_they_didnt_join(self):
        """Trying to leave a classroom without being a member returns 404."""
        other_room = Classroom.objects.create(teacher=self.teacher, name='Other Room')
        url = reverse('classroom-leave', kwargs={'pk': other_room.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 5. TEACHER STUDENT LIST TESTS
# =============================================================================

class TeacherStudentListTest(APITestCase):
    """Tests for the teacher viewing students in their classroom."""

    def setUp(self):
        self.teacher = make_teacher('list_teacher')
        self.other_teacher = make_teacher('list_other_teacher')
        self.student1 = make_student('list_student1')
        self.student2 = make_student('list_student2')
        self.classroom = Classroom.objects.create(teacher=self.teacher, name='List Room')
        ClassroomMembership.objects.create(student=self.student1, classroom=self.classroom)
        ClassroomMembership.objects.create(student=self.student2, classroom=self.classroom)
        self.client.force_authenticate(user=self.teacher)

    def test_teacher_can_see_students_in_own_classroom(self):
        """GET /api/classrooms/<id>/students/ returns all members."""
        url = reverse('classroom-students', kwargs={'pk': self.classroom.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_teacher_cannot_see_students_in_another_classroom(self):
        """Other teacher's classroom returns 404 (not visible to this teacher)."""
        other_room = Classroom.objects.create(teacher=self.other_teacher, name='Other Room')
        url = reverse('classroom-students', kwargs={'pk': other_room.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 6. PERMISSION ENFORCEMENT TESTS
# =============================================================================

class PermissionTest(APITestCase):
    """Tests that role-based access is correctly enforced."""

    def setUp(self):
        self.student = make_student('perm_student')
        self.pending_teacher = make_teacher('perm_pending', approved=False)
        self.list_url = reverse('classroom-list-create')
        self.join_url = reverse('classroom-join')

    def test_unauthenticated_user_cannot_access_classrooms(self):
        """No token = 401 on all endpoints."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_create_classroom(self):
        """Students must get 403 when trying to create a classroom."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.list_url, {'name': 'Hack'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_teacher_cannot_create_classroom(self):
        """Unapproved teacher cannot create classrooms (403)."""
        self.client.force_authenticate(user=self.pending_teacher)
        response = self.client.post(self.list_url, {'name': 'Hack'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_list_teacher_classrooms(self):
        """Students cannot call the teacher list endpoint (403)."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_classrooms_requires_student_role(self):
        """An approved teacher calling /my/ should get 403."""
        teacher = make_teacher('perm_teacher')
        self.client.force_authenticate(user=teacher)
        url = reverse('my-classrooms')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
