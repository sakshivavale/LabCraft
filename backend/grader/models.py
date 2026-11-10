"""
grader/models.py

Defines the database models for the Automated Grading Engine module:
  1. TestCase      — Input/output pairs attached to an assignment (public or hidden).
  2. GradingResult — Execution log, status, and score for a code submission.

Design decisions:
  - TestCase belongs to an Assignment (ForeignKey).
  - When an assignment is deleted, its test cases are deleted (CASCADE).
  - TestCase has an `is_hidden` boolean flag:
      * Public test cases (is_hidden=False) are visible to students for debugging.
      * Hidden test cases (is_hidden=True) are only visible to teachers.
        They prevent students from hardcoding answers to pass tests.
  - GradingResult is linked 1-to-1 with a Submission:
      * Stores overall outcome (ACCEPTED, WRONG_ANSWER, etc.).
      * Stores test pass count and marks awarded.
      * Stores structured JSON execution logs for detailed review.
"""

from django.db import models
from django.core.validators import MinValueValidator
from assignments.models import Assignment
from submissions.models import Submission


# =============================================================================
# 1. TEST CASE MODEL
# =============================================================================

class TestCase(models.Model):
    """
    Represents an automated verification test case for a programming assignment.

    Each test case provides:
      - input_data: Text fed to the student's program via standard input (stdin).
      - expected_output: Text the program is expected to print to standard output (stdout).
      - is_hidden: Whether students can see the input/output details.
      - time_limit: Max execution time allowed in seconds before TLE.
      - memory_limit: Max RAM allowed inside the container (e.g. 128m, 256m).
    """

    # Which assignment this test case tests
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='test_cases',
        help_text="The assignment this test case validates."
    )

    # Standard input passed to the running code
    input_data = models.TextField(
        blank=True,
        default='',
        help_text="Input data passed to the program via stdin."
    )

    # Expected standard output to compare against
    expected_output = models.TextField(
        help_text="Expected stdout from the program."
    )

    # Hidden flag — critical for contest / exam honesty
    is_hidden = models.BooleanField(
        default=False,
        help_text="If True, test case input/output is kept secret from students."
    )

    # Execution limits per test case
    time_limit = models.FloatField(
        default=2.0,
        validators=[MinValueValidator(0.1)],
        help_text="Execution time limit in seconds (default: 2.0s)."
    )

    memory_limit = models.CharField(
        max_length=10,
        default='128m',
        help_text="Memory limit for the container (e.g. '128m', '256m')."
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Test Case'
        verbose_name_plural = 'Test Cases'

    def __str__(self):
        visibility = "Hidden" if self.is_hidden else "Public"
        return f"TestCase #{self.id} for '{self.assignment.title}' ({visibility})"


# =============================================================================
# 2. GRADING RESULT MODEL
# =============================================================================

class GradingResult(models.Model):
    """
    Stores the outcome of executing a student's submission inside the sandbox.

    Tracks:
      - submission: Which submission was evaluated.
      - status: Overall outcome (ACCEPTED, WRONG_ANSWER, COMPILE_ERROR, etc.).
      - passed_count: Number of test cases passed.
      - total_count: Total number of test cases evaluated.
      - score: Calculated marks awarded (proportional to passed test cases).
      - execution_log: Detailed list of test case runs (timings, diffs, errors).
    """

    class Outcome(models.TextChoices):
        ACCEPTED              = 'accepted',              'Accepted'
        WRONG_ANSWER          = 'wrong_answer',          'Wrong Answer'
        COMPILE_ERROR         = 'compile_error',         'Compile Error'
        RUNTIME_ERROR         = 'runtime_error',         'Runtime Error'
        TIME_LIMIT_EXCEEDED   = 'time_limit_exceeded',   'Time Limit Exceeded'
        MEMORY_LIMIT_EXCEEDED = 'memory_limit_exceeded', 'Memory Limit Exceeded'
        SYSTEM_ERROR          = 'system_error',          'System Error'

    # One-to-one relationship with submission
    submission = models.OneToOneField(
        Submission,
        on_delete=models.CASCADE,
        related_name='grading_result',
        help_text="The submission that was graded."
    )

    # Final overall outcome
    status = models.CharField(
        max_length=25,
        choices=Outcome.choices,
        default=Outcome.SYSTEM_ERROR,
        help_text="Overall grading status for this submission."
    )

    # Test case counters
    total_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of test cases run."
    )

    passed_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of test cases successfully passed."
    )

    # Score awarded (out of assignment max_marks)
    score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Marks awarded based on passed test cases."
    )

    # Detailed execution logs per test case stored as JSON
    # Format:
    # [
    #   {
    #     "test_case_id": 1,
    #     "is_hidden": false,
    #     "status": "accepted",
    #     "time_taken": 0.045,
    #     "stdout": "...",
    #     "expected": "...",
    #     "error": ""
    #   }
    # ]
    execution_log = models.JSONField(
        default=list,
        blank=True,
        help_text="Structured JSON logs of per-test-case execution."
    )

    # Error message if compilation or container setup failed
    error_message = models.TextField(
        blank=True,
        default='',
        help_text="Compiler or sandbox error message, if any."
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Grading Result'
        verbose_name_plural = 'Grading Results'

    def __str__(self):
        return f"Result #{self.id} for Submission #{self.submission.id}: {self.status} ({self.passed_count}/{self.total_count})"

    @property
    def pass_percentage(self):
        """Percentage of test cases passed (0.0 to 100.0)."""
        if self.total_count == 0:
            return 0.0
        return round((self.passed_count / self.total_count) * 100.0, 2)
