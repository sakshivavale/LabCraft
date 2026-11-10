"""
submissions/models.py

Defines the Submission model for the Code Editor & Submissions module.

What is a Submission?
  When a student writes code in the Monaco editor and clicks "Submit",
  their source code is sent to the server and stored as a Submission.

  The submission is then picked up by the Grading Engine (Module 5)
  which runs it inside a Docker container and returns a result.
  For now (Module 4), we only STORE the submission — no code is executed.

Design decisions:
  - Submission belongs to ONE assignment (ForeignKey).
  - Submission is made by ONE student (ForeignKey).
  - We store the source code as text (no file uploads — simpler and safer).
  - Status progresses: 'pending' → 'running' → 'accepted'/'wrong_answer'/etc.
    (Status is updated by the grader in Module 5.)
  - A student can submit MULTIPLE times (no unique constraint on student+assignment).
    Each resubmission creates a new record. This preserves history.
  - Submissions after the deadline are REJECTED by the view (not the model).
    The model itself doesn't enforce it so the grader can still update old records.
"""

from django.db import models
from django.conf import settings     # gives us AUTH_USER_MODEL safely
from django.utils import timezone    # for timezone-aware datetime comparisons

from assignments.models import Assignment   # reuse Assignment model from Module 3


# =============================================================================
# SUBMISSION MODEL
# =============================================================================

class Submission(models.Model):
    """
    Represents a student's code submission for a programming assignment.

    Relationship overview:
      - assignment → ForeignKey → Assignment (from Module 3)
      - student    → ForeignKey → accounts.User (the student who submitted)

    Status flow:
      pending → running → accepted / wrong_answer / error / time_limit_exceeded
      (Status is updated by the Docker grader in Module 5.)
    """

    # ------------------------------------------------------------------
    # SUBMISSION STATUS CHOICES
    # These are the possible states a submission can be in.
    # Using TextChoices keeps the allowed values clear and documented.
    # ------------------------------------------------------------------
    class Status(models.TextChoices):
        PENDING              = 'pending',              'Pending'                # just submitted, not yet graded
        RUNNING              = 'running',              'Running'                # grader is executing it now
        ACCEPTED             = 'accepted',             'Accepted'               # all test cases passed ✅
        WRONG_ANSWER         = 'wrong_answer',         'Wrong Answer'           # output doesn't match expected ❌
        RUNTIME_ERROR        = 'runtime_error',        'Runtime Error'          # code crashed during execution
        COMPILE_ERROR        = 'compile_error',        'Compile Error'          # code has syntax errors
        TIME_LIMIT_EXCEEDED  = 'time_limit_exceeded',  'Time Limit Exceeded'    # code took too long
        MEMORY_LIMIT_EXCEEDED= 'memory_limit_exceeded','Memory Limit Exceeded'  # code used too much memory

    # ------------------------------------------------------------------
    # ASSIGNMENT — which assignment this submission is for.
    # ForeignKey = one assignment can have MANY submissions (from many students,
    # each potentially submitting multiple times).
    # on_delete=CASCADE: if assignment is deleted, all its submissions go too.
    # related_name='submissions' lets us do: assignment.submissions.all()
    # ------------------------------------------------------------------
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,        # delete submissions when assignment deleted
        related_name='submissions',      # assignment.submissions.all()
        help_text="The assignment this submission is for."
    )

    # ------------------------------------------------------------------
    # STUDENT — who submitted this code.
    # ForeignKey = one student can submit many times (multiple submissions).
    # on_delete=CASCADE: if student account is deleted, delete their submissions.
    # related_name='submissions' lets us do: student.submissions.all()
    # ------------------------------------------------------------------
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,        # points to accounts.User (custom model)
        on_delete=models.CASCADE,        # delete submissions if student is deleted
        related_name='submissions',      # student.submissions.all()
        limit_choices_to={'role': 'student'},
        help_text="The student who submitted this code."
    )

    # ------------------------------------------------------------------
    # SOURCE CODE — the actual code the student wrote.
    # We store it as text (TextField has no max length limit).
    # WHY TextField not FileField? Text is simpler — no file storage needed,
    # easier to pass to the Docker grader, and easier to display in the editor.
    # ------------------------------------------------------------------
    source_code = models.TextField(
        help_text="The student's submitted source code."
    )

    # ------------------------------------------------------------------
    # LANGUAGE — which programming language the student used.
    # Must match one of the Assignment.Language choices.
    # WHY store it here? The assignment supports one language, so we
    # store the assignment's language at submission time. This future-proofs
    # us if assignments ever support multiple languages.
    # ------------------------------------------------------------------
    language = models.CharField(
        max_length=20,
        choices=Assignment.Language.choices,   # reuse the same language list as assignments
        help_text="Programming language used for this submission."
    )

    # ------------------------------------------------------------------
    # STATUS — where this submission is in the grading pipeline.
    # Starts as 'pending'. Module 5 (grader) will update it.
    # ------------------------------------------------------------------
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.PENDING,          # all submissions start as pending
        help_text="Current grading status of this submission."
    )

    # ------------------------------------------------------------------
    # SUBMITTED AT — exact time the student clicked "Submit".
    # auto_now_add=True: set automatically once when the record is created.
    # WHY store this? Needed to enforce deadlines and to show submission history.
    # ------------------------------------------------------------------
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the student submitted their code."
    )

    # ------------------------------------------------------------------
    # FEEDBACK — optional message from the grader (Module 5 will fill this).
    # e.g. "Test case 3 failed: expected 42, got 41"
    # Blank by default — Module 4 leaves it empty; Module 5 populates it.
    # ------------------------------------------------------------------
    feedback = models.TextField(
        blank=True,
        default='',
        help_text="Grader feedback (populated by Module 5 grading engine)."
    )

    class Meta:
        # Newest submissions first — students see their latest submission at the top
        ordering = ['-submitted_at']
        verbose_name = 'Submission'
        verbose_name_plural = 'Submissions'

    def __str__(self):
        """
        Human-readable string — shown in Django Admin, logs, and the shell.
        Example: "alice → Lab 1: Fibonacci (pending)"
        """
        return f"{self.student.username} → {self.assignment.title} ({self.status})"

    # ------------------------------------------------------------------
    # COMPUTED PROPERTY — is this submission the latest one by this student
    # for this assignment? Useful for display and grading.
    # ------------------------------------------------------------------
    @property
    def is_late(self):
        """
        Return True if this submission was made after the assignment's due_date.

        WHY store this as a property (not a DB field)?
          The due_date can change (teacher might extend it). A property
          always uses the CURRENT due_date at read time — no stale data.

        If no due_date is set, the assignment never expires → never late.
        """
        if self.assignment.due_date is None:
            return False    # no deadline = no late submissions
        return self.submitted_at > self.assignment.due_date
