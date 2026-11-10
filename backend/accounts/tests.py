"""
accounts/tests.py

Tests for the Accounts & Authentication module.

Why write tests?
  Tests are automated checks that verify our code works correctly.
  Run them with:  python manage.py test accounts

Each test class focuses on one area.
Each test method starts with 'test_' so Django finds it automatically.

Test design rule: each test should check ONE thing.
If a test fails, you know exactly what broke.
"""

from django.test import TestCase                   # for model/DB tests
from django.urls import reverse                    # converts URL name → actual path
from rest_framework.test import APITestCase        # for API endpoint tests
from rest_framework import status                  # HTTP status code constants (200, 201, 400, etc.)
from django.contrib.auth import get_user_model

User = get_user_model()


# =============================================================================
# 1. MODEL TESTS
#    Test the User model itself — fields, properties, password storage.
# =============================================================================

class UserModelTest(TestCase):
    """Tests for the custom User model."""

    def test_create_student_has_correct_role(self):
        """A user created with role=STUDENT should have is_student=True."""
        user = User.objects.create_user(
            username='student_model_test',
            email='student@model.test',
            password='StrongPass123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.is_student)       # property check
        self.assertFalse(user.is_teacher)      # opposite role should be False

    def test_student_is_auto_approved(self):
        """When we set is_approved=True for student, it stays True."""
        user = User.objects.create_user(
            username='student_approved',
            email='student_approved@model.test',
            password='StrongPass123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )
        self.assertTrue(user.is_approved)

    def test_create_teacher_pending_approval(self):
        """A teacher created with is_approved=False cannot be considered approved."""
        user = User.objects.create_user(
            username='teacher_pending',
            email='teacher_pending@model.test',
            password='StrongPass123!',
            role=User.Role.TEACHER,
            is_approved=False,
        )
        self.assertTrue(user.is_teacher)
        self.assertFalse(user.is_approved)
        self.assertFalse(user.is_teacher_approved)   # combined property

    def test_teacher_is_approved_after_flag_set(self):
        """Setting is_approved=True on a teacher makes is_teacher_approved True."""
        user = User.objects.create_user(
            username='teacher_approved',
            email='teacher_approved@model.test',
            password='StrongPass123!',
            role=User.Role.TEACHER,
            is_approved=True,
        )
        self.assertTrue(user.is_teacher_approved)

    def test_password_is_never_stored_as_plain_text(self):
        """
        CRITICAL SECURITY TEST.
        The raw password string should NEVER equal the stored password.
        Django hashes passwords using PBKDF2 before saving.
        """
        raw_password = 'StrongPass123!'
        user = User.objects.create_user(
            username='secure_user',
            email='secure@model.test',
            password=raw_password,
        )
        # The stored value should be a hash like 'pbkdf2_sha256$390000$...'
        self.assertNotEqual(user.password, raw_password)
        # But check_password() should still verify the raw password correctly
        self.assertTrue(user.check_password(raw_password))

    def test_email_is_required_to_be_unique(self):
        """Two users cannot share the same email address (DB-level constraint)."""
        from django.db import IntegrityError
        User.objects.create_user(
            username='user_a',
            email='shared@model.test',
            password='StrongPass123!',
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username='user_b',
                email='shared@model.test',   # same email — should fail
                password='StrongPass123!',
            )

    def test_str_method_returns_username_and_role(self):
        """__str__ should return 'username (Role)' for display in Admin."""
        user = User.objects.create_user(
            username='display_user',
            email='display@model.test',
            password='StrongPass123!',
            role=User.Role.TEACHER,
        )
        self.assertIn('display_user', str(user))
        self.assertIn('Teacher', str(user))


# =============================================================================
# 2. STUDENT REGISTRATION TESTS
#    Test POST /api/auth/register/student/
# =============================================================================

class StudentRegistrationTest(APITestCase):
    """Tests for the student registration endpoint."""

    def setUp(self):
        """
        setUp() runs before EACH test method.
        We define the URL and valid data once here to avoid repetition.
        reverse() converts the URL name to the actual path.
        """
        self.url = reverse('student-register')   # → '/api/auth/register/student/'
        self.valid_data = {
            'username':   'newstudent',
            'email':      'newstudent@labcraft.test',
            'first_name': 'New',
            'last_name':  'Student',
            'password':   'StrongPass123!',
            'password2':  'StrongPass123!',
        }

    def test_student_registration_returns_201(self):
        """Valid registration data should create a user and return 201 Created."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_registered_student_has_correct_role(self):
        """The created user should have role='student'."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.data['user']['role'], 'student')

    def test_student_is_immediately_approved(self):
        """Students should have is_approved=True right after registration."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertTrue(response.data['user']['is_approved'])

    def test_response_does_not_contain_password(self):
        """SECURITY: the API response must never include the password."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertNotIn('password', response.data)
        self.assertNotIn('password', response.data.get('user', {}))

    def test_password_mismatch_returns_400(self):
        """If password and password2 don't match, return 400 Bad Request."""
        data = {**self.valid_data, 'password2': 'DifferentPass!'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_returns_400(self):
        """Password '123' is too weak — Django validators should reject it."""
        data = {**self.valid_data, 'password': '123', 'password2': '123'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_returns_400(self):
        """Registering a second time with the same email should fail."""
        self.client.post(self.url, self.valid_data, format='json')
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_username_returns_400(self):
        """Registering a second time with the same username should fail."""
        self.client.post(self.url, self.valid_data, format='json')
        second_attempt = {**self.valid_data, 'email': 'different@labcraft.test'}
        response = self.client.post(self.url, second_attempt, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_required_field_returns_400(self):
        """Omitting a required field (e.g. email) should return 400."""
        data = {**self.valid_data}
        del data['email']
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# 3. TEACHER REGISTRATION TESTS
#    Test POST /api/auth/register/teacher/
# =============================================================================

class TeacherRegistrationTest(APITestCase):
    """Tests for the teacher registration endpoint."""

    def setUp(self):
        self.url = reverse('teacher-register')
        self.valid_data = {
            'username':   'newteacher',
            'email':      'newteacher@labcraft.test',
            'first_name': 'New',
            'last_name':  'Teacher',
            'password':   'StrongPass123!',
            'password2':  'StrongPass123!',
        }

    def test_teacher_registration_returns_201(self):
        """Valid teacher registration should return 201."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_registered_teacher_has_correct_role(self):
        """Created user should have role='teacher'."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.data['user']['role'], 'teacher')

    def test_teacher_starts_as_not_approved(self):
        """CRITICAL: teacher must NOT be approved immediately — needs admin review."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertFalse(response.data['user']['is_approved'])

    def test_response_does_not_contain_password(self):
        """SECURITY: no password in response."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertNotIn('password', response.data.get('user', {}))

    def test_pending_message_in_response(self):
        """Response message should inform the teacher to wait for approval."""
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertIn('pending', response.data['message'].lower())


# =============================================================================
# 4. LOGIN TESTS
#    Test POST /api/auth/login/
# =============================================================================

class LoginTest(APITestCase):
    """Tests for the JWT login endpoint."""

    def setUp(self):
        self.url = reverse('token-obtain-pair')

        # Create an approved student
        self.student = User.objects.create_user(
            username='login_student',
            email='login_student@labcraft.test',
            password='StrongPass123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )

        # Create an unapproved teacher
        self.pending_teacher = User.objects.create_user(
            username='pending_teacher',
            email='pending_teacher@labcraft.test',
            password='StrongPass123!',
            role=User.Role.TEACHER,
            is_approved=False,
        )

        # Create an approved teacher
        self.approved_teacher = User.objects.create_user(
            username='approved_teacher',
            email='approved_teacher@labcraft.test',
            password='StrongPass123!',
            role=User.Role.TEACHER,
            is_approved=True,
        )

    def test_student_login_returns_tokens(self):
        """Approved student should receive access and refresh tokens on login."""
        response = self.client.post(
            self.url,
            {'username': 'login_student', 'password': 'StrongPass123!'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)     # JWT access token present
        self.assertIn('refresh', response.data)    # JWT refresh token present

    def test_login_response_includes_user_info(self):
        """Login response should include user role and ID (from our custom serializer)."""
        response = self.client.post(
            self.url,
            {'username': 'login_student', 'password': 'StrongPass123!'},
            format='json'
        )
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], 'student')
        self.assertIn('id', response.data['user'])

    def test_login_response_never_contains_password(self):
        """SECURITY: password must never appear in login response."""
        response = self.client.post(
            self.url,
            {'username': 'login_student', 'password': 'StrongPass123!'},
            format='json'
        )
        self.assertNotIn('password', response.data)
        self.assertNotIn('password', response.data.get('user', {}))

    def test_pending_teacher_login_is_blocked(self):
        """
        CRITICAL: teacher with is_approved=False must NOT receive tokens.
        Even with correct credentials, login should fail with 401.
        """
        response = self.client.post(
            self.url,
            {'username': 'pending_teacher', 'password': 'StrongPass123!'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)   # no token issued

    def test_approved_teacher_can_login(self):
        """Approved teacher should receive tokens normally."""
        response = self.client.post(
            self.url,
            {'username': 'approved_teacher', 'password': 'StrongPass123!'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_wrong_password_returns_401(self):
        """Wrong password should return 401 Unauthorized."""
        response = self.client.post(
            self.url,
            {'username': 'login_student', 'password': 'WrongPassword!'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_returns_401(self):
        """Login with a username that doesn't exist should return 401."""
        response = self.client.post(
            self.url,
            {'username': 'nobody', 'password': 'StrongPass123!'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# 5. USER PROFILE TESTS
#    Test GET/PATCH /api/auth/profile/
# =============================================================================

class UserProfileTest(APITestCase):
    """Tests for the profile view/update endpoint."""

    def setUp(self):
        self.url = reverse('user-profile')
        self.user = User.objects.create_user(
            username='profile_user',
            email='profile@labcraft.test',
            password='StrongPass123!',
            first_name='Profile',
            last_name='User',
            role=User.Role.STUDENT,
            is_approved=True,
        )

    def test_unauthenticated_user_cannot_access_profile(self):
        """Without a valid token, the profile endpoint should return 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_view_profile(self):
        """Authenticated user should get their own profile data."""
        # force_authenticate bypasses JWT for testing purposes
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'profile_user')
        self.assertEqual(response.data['email'], 'profile@labcraft.test')

    def test_user_can_update_first_name(self):
        """PATCH with new first_name should update and return new value."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'first_name': 'Updated'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()   # reload from DB to confirm it was saved
        self.assertEqual(self.user.first_name, 'Updated')

    def test_user_cannot_change_own_role(self):
        """Role should be read-only — user cannot promote themselves."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'role': 'teacher'}, format='json')
        # Even if 200, the role in DB should not have changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.STUDENT)

    def test_profile_response_has_no_password(self):
        """Profile endpoint must never expose password."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertNotIn('password', response.data)


# =============================================================================
# 6. TEACHER APPROVAL TESTS (Admin actions)
#    Test PATCH /api/auth/admin/teachers/<pk>/approve/
# =============================================================================

class TeacherApprovalTest(APITestCase):
    """Tests for the admin teacher approval endpoints."""

    def setUp(self):
        # Create a Django admin (superuser = is_staff=True + is_superuser=True)
        self.admin = User.objects.create_superuser(
            username='admin_user',
            email='admin@labcraft.test',
            password='AdminPass123!',
        )

        # Create a regular student (should NOT be able to approve teachers)
        self.student = User.objects.create_user(
            username='regular_student',
            email='regular@labcraft.test',
            password='StrongPass123!',
            role=User.Role.STUDENT,
            is_approved=True,
        )

        # Teacher awaiting approval
        self.pending_teacher = User.objects.create_user(
            username='pending_t',
            email='pending_t@labcraft.test',
            password='StrongPass123!',
            role=User.Role.TEACHER,
            is_approved=False,
        )

    def test_admin_can_see_pending_teachers(self):
        """Admin should get a list of unapproved teachers."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('pending-teachers')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)   # one pending teacher in setUp

    def test_student_cannot_see_pending_teachers(self):
        """Non-admin should get 403 Forbidden on the pending teachers list."""
        self.client.force_authenticate(user=self.student)
        url = reverse('pending-teachers')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_approve_teacher(self):
        """Admin approving a teacher should set is_approved=True in DB."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('approve-teacher', kwargs={'pk': self.pending_teacher.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Reload from DB and confirm change was saved
        self.pending_teacher.refresh_from_db()
        self.assertTrue(self.pending_teacher.is_approved)

    def test_non_admin_cannot_approve_teacher(self):
        """Regular student attempting to approve a teacher should get 403."""
        self.client.force_authenticate(user=self.student)
        url = reverse('approve-teacher', kwargs={'pk': self.pending_teacher.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_nonexistent_teacher_returns_404(self):
        """Approving a teacher ID that doesn't exist should return 404."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('approve-teacher', kwargs={'pk': 99999})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_after_approval_teacher_can_login(self):
        """
        End-to-end test: approve teacher → verify they can now log in.
        This tests the full flow from admin action to teacher access.
        """
        # Step 1: Admin approves the teacher
        self.client.force_authenticate(user=self.admin)
        approve_url = reverse('approve-teacher', kwargs={'pk': self.pending_teacher.pk})
        self.client.patch(approve_url)

        # Step 2: Teacher tries to log in (should now succeed)
        self.client.force_authenticate(user=None)   # log out admin
        login_url = reverse('token-obtain-pair')
        response = self.client.post(
            login_url,
            {'username': 'pending_t', 'password': 'StrongPass123!'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_admin_can_revoke_teacher_approval(self):
        """Admin should be able to revoke an approved teacher's access."""
        # First approve the teacher
        self.pending_teacher.is_approved = True
        self.pending_teacher.save()

        self.client.force_authenticate(user=self.admin)
        url = reverse('revoke-teacher', kwargs={'pk': self.pending_teacher.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.pending_teacher.refresh_from_db()
        self.assertFalse(self.pending_teacher.is_approved)
