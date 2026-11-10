"""
assignments/serializers.py

Serializers for the Assignment Management module.

They convert Assignment model instances to/from JSON for the React frontend.

We have three serializers:
  - AssignmentListSerializer   : compact, for list views (many assignments)
  - AssignmentDetailSerializer : full details, for single assignment view
  - AssignmentWriteSerializer  : accepts teacher input for create / update
"""

from rest_framework import serializers
from django.utils import timezone                           # for due_date future-check

from .models import Assignment
from accounts.serializers import UserProfileSerializer      # reuse safe user display


# =============================================================================
# 1. ASSIGNMENT LIST SERIALIZER
#    Lightweight — used when listing many assignments.
#    Does NOT include the full instructions text (too heavy for a list).
# =============================================================================

class AssignmentListSerializer(serializers.ModelSerializer):
    """
    Compact assignment representation for list views.
    Shows classroom name and computed properties instead of nested objects.
    """

    # SerializerMethodField lets us compute a custom value with a Python method.
    # WHY? We want to show classroom_name as a string, not a full nested object.
    classroom_name = serializers.SerializerMethodField(
        help_text="Name of the classroom this assignment belongs to."
    )

    # WHY no 'source' on status and is_past_due?
    # DRF raises AssertionError if source == field name (it's redundant and confusing).
    # These field names MATCH the @property names on the model, so DRF resolves them automatically.
    status = serializers.CharField(read_only=True)
    is_past_due = serializers.BooleanField(read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id',
            'title',
            'description',      # short summary (full instructions in detail view)
            'classroom_id',     # just the ID, not the whole classroom object
            'classroom_name',   # human-readable name (computed)
            'language',         # programming language
            'difficulty',       # easy / medium / hard
            'due_date',         # deadline
            'max_marks',        # max score
            'is_published',     # draft vs published
            'status',           # 'draft', 'open', or 'closed' (computed @property)
            'is_past_due',      # True if deadline has passed (computed @property)
            'created_at',
        ]
        # All fields are read-only in this serializer — it's only for displaying data
        read_only_fields = [
            'id', 'classroom_id', 'classroom_name', 'status', 'is_past_due', 'created_at'
        ]

    def get_classroom_name(self, obj):
        """
        Return the name of the classroom this assignment belongs to.
        'obj' is the Assignment instance being serialized.
        """
        return obj.classroom.name


# =============================================================================
# 2. ASSIGNMENT DETAIL SERIALIZER
#    Full details — used when viewing a single assignment.
#    Includes instructions text and nested teacher info.
# =============================================================================

class AssignmentDetailSerializer(serializers.ModelSerializer):
    """
    Full assignment data including instructions and nested creator info.
    Used for GET /assignments/<id>/ and GET /assignments/<id>/student/ endpoints.
    """

    # Nest the full teacher profile (read-only — teacher is set by the view)
    # WHY nest? The frontend can display teacher's name without an extra API call.
    created_by = UserProfileSerializer(read_only=True)

    # classroom_name as a simple string — the frontend doesn't need the full classroom object
    classroom_name = serializers.SerializerMethodField(
        help_text="Name of the classroom this assignment belongs to."
    )

    # Computed properties from the model — read-only, no source= needed
    status = serializers.CharField(read_only=True)
    is_past_due = serializers.BooleanField(read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id',
            'title',
            'description',
            'instructions',     # full step-by-step instructions (not in list view)
            'classroom_id',
            'classroom_name',
            'created_by',       # nested teacher profile
            'language',
            'difficulty',
            'due_date',
            'max_marks',
            'is_published',
            'status',
            'is_past_due',
            'created_at',
            'updated_at',       # when it was last modified
        ]
        read_only_fields = [
            'id', 'classroom_id', 'classroom_name', 'created_by',
            'status', 'is_past_due', 'created_at', 'updated_at'
        ]

    def get_classroom_name(self, obj):
        """Return the name of the classroom this assignment belongs to."""
        return obj.classroom.name


# =============================================================================
# 3. ASSIGNMENT WRITE SERIALIZER
#    Accepts teacher input for creating or updating an assignment.
#    Does NOT include classroom, created_by, or timestamps —
#    those are set by the view or auto-set by Django.
# =============================================================================

class AssignmentWriteSerializer(serializers.ModelSerializer):
    """
    Accepts assignment data from a teacher to create or update an assignment.

    Fields NOT here (deliberately excluded):
      - classroom   → set by the view from the URL (<classroom_id>)
      - created_by  → set by the view from request.user
      - created_at  → auto-set by Django (auto_now_add)
      - updated_at  → auto-set by Django (auto_now)
    """

    class Meta:
        model = Assignment
        fields = [
            'title',          # required — short name
            'description',    # optional — brief summary
            'instructions',   # optional — detailed step-by-step guide
            'due_date',       # optional — deadline (must be future on create)
            'max_marks',      # optional — defaults to 100
            'language',       # required — programming language
            'difficulty',     # optional — defaults to 'medium'
            'is_published',   # optional — defaults to False (draft)
        ]

    def validate_title(self, value):
        """
        Title must not be empty or contain only whitespace.
        WHY? A blank title like "   " is confusing and useless for students.
        """
        if not value.strip():
            raise serializers.ValidationError("Assignment title cannot be blank.")
        return value.strip()   # remove leading/trailing spaces before saving

    def validate_max_marks(self, value):
        """
        max_marks must be greater than zero.
        WHY? An assignment worth 0 marks makes no sense.
        PositiveIntegerField already blocks negative numbers, but allows 0.
        We add this extra check to block 0 as well.
        """
        if value < 1:
            raise serializers.ValidationError("Max marks must be at least 1.")
        return value

    def validate_due_date(self, value):
        """
        If a due_date is provided on CREATE, it must be in the future.
        On UPDATE (PATCH), we allow past dates so teachers can keep historical data.

        WHY check self.instance?
          self.instance is None when creating (POST).
          self.instance is the existing Assignment when updating (PATCH).
        """
        if value is not None and self.instance is None:
            # This is a CREATE operation — enforce future date
            if value <= timezone.now():
                raise serializers.ValidationError(
                    "Due date must be in the future when creating an assignment."
                )
        return value
