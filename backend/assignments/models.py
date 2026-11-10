"""
assignments/models.py

Defines the Assignment model for the Assignment Management module.

What is an Assignment?
  A piece of work (a programming task) that a teacher creates inside one of
  their classrooms. Students in that classroom can then view the assignment
  and (in a future module) submit their solutions.

Design decisions:
  - Assignment belongs to ONE classroom (ForeignKey).
  - Only the classroom's teacher creates assignments — enforced in the view.
  - We store: title, description, instructions, due_date, max_marks,
    language, difficulty, is_published, and timestamps.
  - We do NOT store submissions here — that is a separate module (Module 4).
"""

from django.db import models
from django.conf import settings     # gives us AUTH_USER_MODEL safely
from django.utils import timezone    # for timezone-aware datetime comparisons

from classrooms.models import Classroom   # reuse the Classroom model from Module 2


# =============================================================================
# ASSIGNMENT MODEL
# =============================================================================

class Assignment(models.Model):
    """
    Represents a programming assignment created by a teacher inside a classroom.

    Relationship overview:
      - classroom → ForeignKey → Classroom (from Module 2)
      - created_by → ForeignKey → accounts.User (the teacher who made it)
      - Students who are members of the classroom can VIEW published assignments.
      - Submission of solutions is handled in a separate module (Module 4).
    """

    # ------------------------------------------------------------------
    # PROGRAMMING LANGUAGE CHOICES
    # Using TextChoices keeps the allowed values clear and self-documented.
    # Only these languages are accepted — prevents arbitrary strings.
    # ------------------------------------------------------------------
    class Language(models.TextChoices):
        PYTHON     = 'python',     'Python'
        JAVA       = 'java',       'Java'
        C          = 'c',          'C'
        CPP        = 'cpp',        'C++'
        JAVASCRIPT = 'javascript', 'JavaScript'
        OTHER      = 'other',      'Other'

    # ------------------------------------------------------------------
    # DIFFICULTY LEVEL CHOICES
    # Three levels, stored as short strings, displayed with capital labels.
    # ------------------------------------------------------------------
    class Difficulty(models.TextChoices):
        EASY   = 'easy',   'Easy'
        MEDIUM = 'medium', 'Medium'
        HARD   = 'hard',   'Hard'

    # ------------------------------------------------------------------
    # CLASSROOM — which classroom this assignment belongs to.
    # ForeignKey = one classroom can have MANY assignments,
    #              but each assignment belongs to exactly ONE classroom.
    # on_delete=CASCADE: if the classroom is deleted, all its assignments
    # are deleted too. Orphan assignments with no classroom have no use.
    # related_name='assignments' lets us do: classroom.assignments.all()
    # ------------------------------------------------------------------
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,       # delete assignments when classroom deleted
        related_name='assignments',     # classroom.assignments.all()
        help_text="The classroom this assignment belongs to."
    )

    # ------------------------------------------------------------------
    # CREATED BY — which teacher created this assignment.
    # We store this separately from classroom.teacher because it lets us
    # quickly query "all assignments by this teacher" without joining
    # through the classroom table. It also acts as a safety check in
    # views: we verify created_by == request.user before allowing edit/delete.
    # ------------------------------------------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,            # points to accounts.User (custom model)
        on_delete=models.CASCADE,            # delete assignments if teacher deleted
        related_name='created_assignments',  # teacher.created_assignments.all()
        limit_choices_to={'role': 'teacher'},
        help_text="The teacher who created this assignment."
    )

    # ------------------------------------------------------------------
    # TITLE — required short name for the assignment.
    # e.g. "Lab 3: Linked Lists"
    # ------------------------------------------------------------------
    title = models.CharField(
        max_length=255,
        help_text="Short title for the assignment, e.g. 'Lab 3: Linked Lists'."
    )

    # ------------------------------------------------------------------
    # DESCRIPTION — a brief summary of what the assignment is about.
    # Optional (blank=True, default='') — teacher may add more in instructions.
    # ------------------------------------------------------------------
    description = models.TextField(
        blank=True,
        default='',
        help_text="Brief description of what the assignment is about."
    )

    # ------------------------------------------------------------------
    # INSTRUCTIONS — the full problem statement / task details.
    # What students read to understand what they must code.
    # Optional so teachers can save a draft without full instructions ready.
    # ------------------------------------------------------------------
    instructions = models.TextField(
        blank=True,
        default='',
        help_text="Full problem statement and instructions for the student."
    )

    # ------------------------------------------------------------------
    # DUE DATE — deadline for submission.
    # null=True + blank=True means it can be left unset (open-ended assignment).
    # DateTimeField (not DateField) so the teacher can set a specific hour/minute.
    # ------------------------------------------------------------------
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Deadline for submission. Leave blank for no deadline."
    )

    # ------------------------------------------------------------------
    # MAX MARKS — maximum score possible for this assignment.
    # PositiveIntegerField: cannot be 0 or negative — only 1 and above.
    # Default 100 is a sensible standard for most assignments.
    # ------------------------------------------------------------------
    max_marks = models.PositiveIntegerField(
        default=100,
        help_text="Maximum marks for this assignment (default: 100)."
    )

    # ------------------------------------------------------------------
    # PROGRAMMING LANGUAGE — which language students must code in.
    # Uses Language TextChoices defined above — only valid choices accepted.
    # default='python' is the most common lab language.
    # ------------------------------------------------------------------
    language = models.CharField(
        max_length=20,
        choices=Language.choices,
        default=Language.PYTHON,
        help_text="Programming language required for this assignment."
    )

    # ------------------------------------------------------------------
    # DIFFICULTY — how hard this assignment is.
    # Uses Difficulty TextChoices — only 'easy', 'medium', 'hard' accepted.
    # default='medium' is a neutral starting point.
    # ------------------------------------------------------------------
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
        help_text="Difficulty level: easy, medium, or hard."
    )

    # ------------------------------------------------------------------
    # IS PUBLISHED — controls student visibility.
    # False (draft): only the teacher can see this assignment.
    # True (published): enrolled students in the classroom can view it.
    # This lets teachers prepare assignments in advance without students
    # seeing them before they are ready.
    # ------------------------------------------------------------------
    is_published = models.BooleanField(
        default=False,
        help_text=(
            "Draft (False): only teacher sees this. "
            "Published (True): enrolled students can view it."
        )
    )

    # ------------------------------------------------------------------
    # TIMESTAMPS — set automatically by Django, never by the user.
    # auto_now_add=True: set ONCE when the record is first created.
    # auto_now=True: updated every single time .save() is called.
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Newest assignments appear first in all querysets by default
        ordering = ['-created_at']
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'

    def __str__(self):
        """
        Human-readable string — shown in Django Admin, logs, and the shell.
        Example: "Lab 3: Linked Lists (Python Lab - Sem 3)"
        """
        return f"{self.title} ({self.classroom.name})"

    # ------------------------------------------------------------------
    # COMPUTED PROPERTIES — read-only helpers used in serializers.
    # Defining them on the model means they work from API, Admin,
    # Django shell, and tests — without duplicating logic.
    # ------------------------------------------------------------------

    @property
    def is_past_due(self):
        """
        Return True if the due date has already passed.

        WHY use timezone.now() instead of datetime.now()?
          Django uses timezone-aware datetimes (USE_TZ=True in settings.py).
          timezone.now() gives the current time WITH timezone info.
          datetime.now() gives a timezone-NAIVE time — comparing the two
          raises a TypeError. Always use timezone.now() in Django.

        If no due_date is set, the assignment never expires → return False.
        """
        if self.due_date is None:
            return False                    # no deadline = never past due
        return timezone.now() > self.due_date   # True if deadline has passed

    @property
    def status(self):
        """
        Return a human-readable status string for the frontend to display.
        Possible values: 'draft', 'open', 'closed'

        Logic:
          - Not published → 'draft'   (teacher hasn't released it yet)
          - Published AND past due_date → 'closed'  (time's up)
          - Published AND open → 'open'  (students can still submit)
        """
        if not self.is_published:
            return 'draft'
        if self.is_past_due:
            return 'closed'
        return 'open'
