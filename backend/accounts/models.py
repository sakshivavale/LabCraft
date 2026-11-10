"""
accounts/models.py

Defines the custom User model for LabCraft.

Why a custom User model?
  Django's default User model only has username/password/email.
  We need extra fields: role (student or teacher) and is_approved
  (whether a teacher has been approved by an admin).

  Django strongly recommends setting a custom User model at the
  START of a project, before the first migration. We follow that here.
"""

from django.contrib.auth.models import AbstractUser  # Django's built-in user with hashing, permissions, etc.
from django.db import models


class User(AbstractUser):
    """
    LabCraft's custom user model.

    Inherits everything from AbstractUser (username, password, email,
    first_name, last_name, is_active, is_staff, date_joined, etc.)
    and adds our own fields on top.
    """

    # ------------------------------------------------------------------
    # Role choices — using TextChoices gives us 'student' and 'teacher'
    # as the values stored in the DB, with human-readable labels.
    # ------------------------------------------------------------------
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'   # stored as 'student' in DB
        TEACHER = 'teacher', 'Teacher'   # stored as 'teacher' in DB

    # ------------------------------------------------------------------
    # Custom fields
    # ------------------------------------------------------------------

    # email must be unique — no two accounts can share an email address
    email = models.EmailField(
        unique=True,
        help_text="Required. Must be unique across all users."
    )

    # Every user is either a student or a teacher
    role = models.CharField(
        max_length=10,
        choices=Role.choices,       # only 'student' or 'teacher' allowed
        default=Role.STUDENT,       # default to student if not specified
        help_text="User's role in LabCraft."
    )

    # Teachers start as not approved; admin must approve them
    # Students are automatically approved on registration
    is_approved = models.BooleanField(
        default=False,
        help_text=(
            "For teachers: must be True (approved by admin) before they can log in. "
            "For students: automatically set to True on registration."
        )
    )

    # ------------------------------------------------------------------
    # Tell Django which field is used to log in (we keep 'username')
    # and which fields are required when creating via CLI.
    # ------------------------------------------------------------------
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'role']   # asked when running createsuperuser

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']       # newest users appear first in lists

    def __str__(self):
        # How this user appears in Django Admin and in logs
        return f"{self.username} ({self.get_role_display()})"

    # ------------------------------------------------------------------
    # Helper properties — makes checks readable: user.is_student
    # instead of user.role == 'student'
    # ------------------------------------------------------------------

    @property
    def is_student(self):
        """Return True if this user is a student."""
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        """Return True if this user is a teacher (approved or not)."""
        return self.role == self.Role.TEACHER

    @property
    def is_teacher_approved(self):
        """Return True only if this user is a teacher AND has been approved."""
        return self.role == self.Role.TEACHER and self.is_approved
