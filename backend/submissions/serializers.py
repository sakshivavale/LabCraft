"""
submissions/serializers.py

Serializers for the Code Editor & Submissions module.

They convert Submission model instances to/from JSON for the React frontend.

Three serializers:
  - SubmissionListSerializer   : compact, for showing submission history list
  - SubmissionDetailSerializer : full detail for viewing one submission
  - SubmissionCreateSerializer : accepts student input (source_code, language)
"""

from rest_framework import serializers
from django.utils import timezone          # for deadline enforcement

from .models import Submission
from accounts.serializers import UserProfileSerializer       # reuse safe user display
from assignments.models import Assignment


# =============================================================================
# 1. SUBMISSION LIST SERIALIZER
#    Lightweight — used when listing many submissions (history view).
#    Does NOT include the full source code (too heavy for a list).
# =============================================================================

class SubmissionListSerializer(serializers.ModelSerializer):
    """
    Compact submission representation for list views.
    Shows assignment name and status without the full source code.
    """

    # SerializerMethodField lets us compute a custom value with a method.
    # WHY? We want assignment_title as a string, not a full nested object.
    assignment_title = serializers.SerializerMethodField(
        help_text="Title of the assignment this submission is for."
    )
    assignment_id = serializers.IntegerField(
        source='assignment.id',
        read_only=True
    )

    # is_late is a @property on the model — read_only, no source= needed
    # (same rule as Module 3: source== field name causes DRF AssertionError)
    is_late = serializers.BooleanField(read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id',
            'assignment_id',
            'assignment_title',   # computed
            'language',
            'status',
            'is_late',            # computed @property
            'submitted_at',
        ]
        read_only_fields = [
            'id', 'assignment_id', 'assignment_title', 'status',
            'is_late', 'submitted_at'
        ]

    def get_assignment_title(self, obj):
        """
        Return the title of the assignment this submission is for.
        'obj' is the Submission instance being serialized.
        """
        return obj.assignment.title


# =============================================================================
# 2. SUBMISSION DETAIL SERIALIZER
#    Full details — used when viewing one specific submission.
#    Includes the source code and feedback.
# =============================================================================

class SubmissionDetailSerializer(serializers.ModelSerializer):
    """
    Full submission data including source code and grader feedback.
    Used for GET /submissions/<id>/
    """

    # Nest the student's profile (read-only — student is set by the view)
    student = UserProfileSerializer(read_only=True)

    # Nested assignment info
    assignment_title = serializers.SerializerMethodField(
        help_text="Title of the assignment."
    )
    assignment_id = serializers.IntegerField(source='assignment.id', read_only=True)
    classroom_id = serializers.IntegerField(
        source='assignment.classroom.id', read_only=True
    )
    classroom_name = serializers.CharField(
        source='assignment.classroom.name', read_only=True
    )

    # Computed property
    is_late = serializers.BooleanField(read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id',
            'assignment_id',
            'assignment_title',
            'classroom_id',
            'classroom_name',
            'student',          # nested student profile
            'source_code',      # the actual code (included in detail view)
            'language',
            'status',
            'feedback',         # grader output (empty until Module 5 runs)
            'is_late',
            'submitted_at',
        ]
        read_only_fields = [
            'id', 'assignment_id', 'assignment_title', 'classroom_id',
            'classroom_name', 'student', 'status', 'feedback', 'is_late', 'submitted_at'
        ]

    def get_assignment_title(self, obj):
        """Return the title of the assignment this submission is for."""
        return obj.assignment.title


# =============================================================================
# 3. SUBMISSION CREATE SERIALIZER
#    Accepts student input for submitting code.
#    Does NOT include assignment, student, status, or submitted_at —
#    those are set by the view or auto-set by Django.
# =============================================================================

class SubmissionCreateSerializer(serializers.ModelSerializer):
    """
    Accepts code submission data from a student.

    Fields NOT here (deliberately excluded):
      - assignment  → set by the view from the URL (<assignment_id>)
      - student     → set by the view from request.user (the JWT token)
      - status      → auto-set to 'pending'
      - submitted_at→ auto-set by Django (auto_now_add)
      - feedback    → filled by Module 5 grader, empty on submission
    """

    class Meta:
        model = Submission
        fields = [
            'source_code',   # required — the code the student wrote
            'language',      # required — which language they used
        ]

    def validate_source_code(self, value):
        """
        Source code must not be empty.
        WHY? An empty submission makes no sense — the student typed nothing.
        """
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Source code cannot be empty. Please write your code before submitting."
            )
        return value

    def validate(self, attrs):
        """
        Cross-field validation.
        Check that the submission language matches the assignment's language.

        WHY validate here (not in validate_language)?
          We need BOTH language AND the assignment object.
          The assignment is passed via context from the view.
          Cross-field validation in validate() gives us access to all fields + context.
        """
        assignment = self.context.get('assignment')
        language = attrs.get('language')

        if assignment and language:
            # The assignment specifies which language students must use.
            # 'other' on the assignment means any language is accepted.
            if assignment.language != 'other' and language != assignment.language:
                raise serializers.ValidationError({
                    'language': (
                        f"This assignment requires {assignment.get_language_display()}. "
                        f"You submitted {dict(Assignment.Language.choices).get(language, language)}."
                    )
                })

        return attrs
