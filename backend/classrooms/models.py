"""
classrooms/models.py

Defines the database models for the Classroom Management module.

Two models:
  1. Classroom — a virtual class created by a teacher.
  2. ClassroomMembership — the join table linking students to classrooms.

Why a separate membership model?
  A classroom has MANY students, and a student can join MANY classrooms.
  This is a many-to-many relationship.
  Django provides ManyToManyField, but we use a custom through model so
  we can store extra data (like the date the student joined).
"""

import uuid                          # Python's built-in unique ID generator
from django.db import models
from django.conf import settings     # gives access to AUTH_USER_MODEL safely


# =============================================================================
# 1. CLASSROOM MODEL
# =============================================================================

class Classroom(models.Model):
    """
    Represents a virtual classroom created by an approved teacher.

    Key design decisions:
      - 'teacher' is a ForeignKey → one teacher can own many classrooms,
        but each classroom has exactly ONE teacher.
      - 'join_code' is unique and auto-generated → students use it to join.
      - 'students' is a many-to-many relation through ClassroomMembership.
    """

    # ------------------------------------------------------------------
    # Teacher who owns this classroom
    # ForeignKey means: "this classroom belongs to one teacher"
    # on_delete=CASCADE means: if the teacher account is deleted,
    # all their classrooms are deleted too.
    # related_name='classrooms' lets us do teacher.classrooms.all()
    # ------------------------------------------------------------------
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,     # points to accounts.User (custom model)
        on_delete=models.CASCADE,     # delete classrooms if teacher is deleted
        related_name='classrooms',    # teacher.classrooms.all() gives all their rooms
        limit_choices_to={'role': 'teacher'},  # DB hint: only teachers should own classrooms
        help_text="The approved teacher who created this classroom."
    )

    # Name of the classroom, e.g. "Data Structures Lab - 2024"
    name = models.CharField(
        max_length=200,
        help_text="Classroom name, e.g. 'Python Lab - Sem 3'"
    )

    # Optional longer description of what this classroom is about
    description = models.TextField(
        blank=True,    # optional — not required
        default='',
        help_text="Optional description of the classroom."
    )

    # ------------------------------------------------------------------
    # Join Code — the secret code students use to enter this classroom.
    # uuid.uuid4() generates a random ID like: a3f2d1b4-9c8e-4f7a-b6d2-...
    # We take the first 8 characters for a short, user-friendly code.
    # unique=True ensures no two classrooms ever share the same code.
    # ------------------------------------------------------------------
    join_code = models.CharField(
        max_length=10,
        unique=True,                       # no duplicates allowed
        blank=True,                        # we generate it in save(), not by the user
        help_text="Unique code students use to join this classroom."
    )

    # Whether this classroom is currently active (teacher can deactivate it)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive classrooms cannot be joined by new students."
    )

    # Timestamps — automatically set by Django
    created_at = models.DateTimeField(auto_now_add=True)   # set once when created
    updated_at = models.DateTimeField(auto_now=True)       # updated every time .save() is called

    # ------------------------------------------------------------------
    # Many-to-many: a classroom has many students, a student joins many classrooms.
    # 'through=ClassroomMembership' means we use our custom join table.
    # ------------------------------------------------------------------
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ClassroomMembership',    # custom join table (defined below)
        related_name='joined_classrooms', # student.joined_classrooms.all()
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']      # newest classrooms first
        verbose_name = 'Classroom'
        verbose_name_plural = 'Classrooms'

    def __str__(self):
        return f"{self.name} (by {self.teacher.username})"

    def save(self, *args, **kwargs):
        """
        Override save() so that the join_code is auto-generated
        the first time a Classroom is created.

        Why here and not in the view?
          Putting the generation in save() means it works no matter
          HOW the classroom is created (API, Admin panel, shell, tests).
        """
        if not self.join_code:    # only generate if the code is empty (first save)
            self.join_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_unique_code():
        """
        Generate a short, unique, uppercase join code.

        Steps:
          1. uuid.uuid4() → random UUID like '3f2d1b4a-9c8e-4f7a-...'
          2. .hex → remove dashes → '3f2d1b4a9c8e4f7a...'
          3. [:8] → take first 8 characters → '3f2d1b4a'
          4. .upper() → make uppercase → '3F2D1B4A'
          5. Loop until we find a code NOT already in the database.
        """
        while True:
            code = uuid.uuid4().hex[:8].upper()   # e.g. 'A3F2D1B4'
            if not Classroom.objects.filter(join_code=code).exists():
                return code    # unique code found — return it

    @property
    def student_count(self):
        """Return how many students are currently in this classroom."""
        return self.students.count()


# =============================================================================
# 2. CLASSROOM MEMBERSHIP MODEL (the join table)
# =============================================================================

class ClassroomMembership(models.Model):
    """
    Records that a specific student has joined a specific classroom.

    Why not use Django's built-in ManyToManyField directly?
      Because we want to store EXTRA INFO about the relationship:
        - When did the student join? (joined_at)
      This is only possible with a custom through model.

    Uniqueness constraint:
      Together, (student, classroom) must be unique.
      This prevents a student from joining the same classroom twice.
    """

    # Which student joined
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,          # if student deleted, remove their memberships
        related_name='memberships',
        limit_choices_to={'role': 'student'},
        help_text="The student who joined the classroom."
    )

    # Which classroom they joined
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,          # if classroom deleted, remove memberships
        related_name='memberships',
        help_text="The classroom the student joined."
    )

    # When they joined
    joined_at = models.DateTimeField(
        auto_now_add=True,     # automatically set to right now when the record is created
        help_text="Timestamp when the student joined the classroom."
    )

    class Meta:
        # THE MOST IMPORTANT CONSTRAINT:
        # A student can only be in a classroom ONCE.
        # unique_together = [('student', 'classroom')] would also work,
        # but constraints is the modern Django way.
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'classroom'],
                name='unique_student_classroom'
            )
        ]
        ordering = ['-joined_at']
        verbose_name = 'Classroom Membership'
        verbose_name_plural = 'Classroom Memberships'

    def __str__(self):
        return f"{self.student.username} in {self.classroom.name}"
