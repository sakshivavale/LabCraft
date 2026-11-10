"""
accounts/permissions.py

Custom DRF permission classes for LabCraft.

How DRF permissions work:
  Every API view can declare permission_classes = [SomePermission].
  Before running the view, DRF calls has_permission() on each class.
  If it returns False, the request is rejected with 403 Forbidden.

We define three role-based permission classes here so other modules
can simply import and use them.
"""

from rest_framework.permissions import BasePermission  # DRF base class for custom permissions


class IsStudent(BasePermission):
    """
    Grants access only to authenticated users whose role is 'student'.

    Usage in a view:
        permission_classes = [IsStudent]
    """

    message = "Access restricted to students only."

    def has_permission(self, request, view):
        # request.user is the currently logged-in user (or AnonymousUser if not logged in)
        # We check three things in order:
        return bool(
            request.user                        # 1. The user object exists
            and request.user.is_authenticated   # 2. They are logged in (not anonymous)
            and request.user.is_student         # 3. Their role is 'student'
        )


class IsTeacher(BasePermission):
    """
    Grants access to authenticated teachers (approved OR pending).

    Usually you want IsApprovedTeacher. Use this only if you need
    to show something even to unapproved teachers (e.g., a 'pending' page).
    """

    message = "Access restricted to teachers only."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_teacher          # role == 'teacher'
        )


class IsApprovedTeacher(BasePermission):
    """
    Grants access only to teachers who have been approved by an admin.

    This is the permission used for all teacher-facing features
    (creating classrooms, setting assignments, etc.).
    """

    message = "Access restricted to approved teachers only. Your account may be pending approval."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_teacher_approved  # is_teacher AND is_approved
        )

