"""
accounts/views.py

API views for the Accounts & Authentication module.

What is a 'view' in Django REST Framework?
  A view is a Python function (or class) that receives an HTTP request,
  does some work (validate data, read/write the database), and returns
  an HTTP response (usually JSON).

We use class-based views (CBVs) from DRF because they handle common
patterns (create, list, retrieve, update) with minimal boilerplate.
"""

from rest_framework import generics, status, permissions   # DRF utilities
from rest_framework.response import Response               # wraps data into a JSON HTTP response
from rest_framework.views import APIView                   # base class for custom API views
from rest_framework_simplejwt.views import TokenObtainPairView  # built-in JWT login view
from rest_framework_simplejwt.views import TokenRefreshView     # built-in token refresh view
from django.contrib.auth import get_user_model             # safe reference to our custom User model

from .serializers import (
    StudentRegistrationSerializer,
    TeacherRegistrationSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    CustomTokenObtainPairSerializer,
)

User = get_user_model()   # = accounts.User


# =============================================================================
# 1. LOGIN VIEW
#    POST /api/auth/login/
#    Uses our custom serializer (blocks unapproved teachers, adds user info).
# =============================================================================

class LoginView(TokenObtainPairView):
    """
    Accepts username + password.
    Returns access token, refresh token, and basic user info.

    - Access token: short-lived (60 min). Send this in the Authorization header.
    - Refresh token: long-lived (7 days). Use to get a new access token.
    - Unapproved teachers receive 401 with a clear message.
    """
    serializer_class = CustomTokenObtainPairSerializer   # swap in our custom serializer


# =============================================================================
# 2. STUDENT REGISTRATION VIEW
#    POST /api/auth/register/student/
# =============================================================================

class StudentRegisterView(generics.CreateAPIView):
    """
    Creates a new Student account.
    No authentication required — anyone can register as a student.
    Student is immediately active (is_approved=True).
    """
    permission_classes = [permissions.AllowAny]   # public endpoint — no login needed
    serializer_class = StudentRegistrationSerializer

    def create(self, request, *args, **kwargs):
        """
        Override create() to return a custom success message
        alongside the new user's profile data.
        """
        serializer = self.get_serializer(data=request.data)   # pass request body to serializer
        serializer.is_valid(raise_exception=True)             # validate; auto-returns 400 on error
        user = serializer.save()                              # calls serializer.create() → saves to DB

        return Response(
            {
                'message': 'Student account created successfully. You can now log in.',
                'user': UserProfileSerializer(user).data,     # return safe user info (no password)
            },
            status=status.HTTP_201_CREATED    # 201 means "resource created"
        )


# =============================================================================
# 3. TEACHER REGISTRATION VIEW
#    POST /api/auth/register/teacher/
# =============================================================================

class TeacherRegisterView(generics.CreateAPIView):
    """
    Creates a new Teacher account with is_approved=False.
    Teacher cannot log in until an admin approves them.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = TeacherRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                'message': (
                    'Teacher registration submitted successfully. '
                    'Your account is pending admin approval. '
                    'You will be able to log in once approved.'
                ),
                'user': UserProfileSerializer(user).data,
            },
            status=status.HTTP_201_CREATED
        )


# =============================================================================
# 4. USER PROFILE VIEW
#    GET  /api/auth/profile/   → view own profile
#    PUT  /api/auth/profile/   → update first_name, last_name, email
#    PATCH /api/auth/profile/  → partial update
# =============================================================================

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Logged-in user can view and update their own profile.
    Role and is_approved are read-only — only admins can change those.
    """
    permission_classes = [permissions.IsAuthenticated]   # must be logged in

    def get_serializer_class(self):
        """
        Use different serializers for reading vs writing.
        GET  → UserProfileSerializer (all fields, read-only)
        PUT/PATCH → UserProfileUpdateSerializer (only editable fields)
        """
        if self.request.method in ('PUT', 'PATCH'):
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    def get_object(self):
        """
        Return the currently logged-in user as the object being operated on.
        (Standard RetrieveUpdateAPIView needs to know WHICH object to fetch.)
        """
        return self.request.user   # from the JWT token in the Authorization header


# =============================================================================
# 5. PENDING TEACHERS LIST  (Admin only)
#    GET /api/auth/admin/teachers/pending/
# =============================================================================

class PendingTeacherListView(generics.ListAPIView):
    """
    Returns all teacher accounts that are waiting for admin approval.
    Only Django admins (is_staff=True) can access this.
    """
    permission_classes = [permissions.IsAdminUser]   # DRF built-in: only is_staff=True users
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        """
        Filter the User table: role == 'teacher' AND is_approved == False.
        """
        return User.objects.filter(
            role=User.Role.TEACHER,
            is_approved=False
        ).order_by('date_joined')   # oldest pending requests first


# =============================================================================
# 6. APPROVE TEACHER  (Admin only)
#    PATCH /api/auth/admin/teachers/<pk>/approve/
# =============================================================================

class ApproveTeacherView(APIView):
    """
    Admin approves a pending teacher by their primary key (pk = database ID).
    Sets is_approved=True so the teacher can now log in.
    """
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        """
        PATCH is used for partial updates (we're only changing one field: is_approved).
        'pk' comes from the URL — e.g. /api/auth/admin/teachers/5/approve/
        """
        try:
            # Look for a teacher user with this exact ID
            user = User.objects.get(pk=pk, role=User.Role.TEACHER)
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if already approved — avoid duplicate approvals
        if user.is_approved:
            return Response(
                {'message': f'Teacher "{user.username}" is already approved.'},
                status=status.HTTP_200_OK
            )

        # Approve the teacher
        user.is_approved = True
        user.save(update_fields=['is_approved'])   # update only this field, not the whole row

        return Response(
            {
                'message': f'Teacher "{user.username}" has been approved. They can now log in.',
                'user': UserProfileSerializer(user).data,
            },
            status=status.HTTP_200_OK
        )


# =============================================================================
# 7. REVOKE TEACHER APPROVAL  (Admin only)
#    PATCH /api/auth/admin/teachers/<pk>/revoke/
# =============================================================================

class RevokeTeacherView(APIView):
    """
    Admin can revoke a previously approved teacher's access.
    Sets is_approved=False so the teacher can no longer log in.
    """
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.TEACHER)
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        user.is_approved = False
        user.save(update_fields=['is_approved'])

        return Response(
            {
                'message': f'Access for teacher "{user.username}" has been revoked.',
                'user': UserProfileSerializer(user).data,
            },
            status=status.HTTP_200_OK
        )
