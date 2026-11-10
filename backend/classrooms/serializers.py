"""
classrooms/serializers.py

Serializers for the Classroom Management module.

They convert Classroom and ClassroomMembership model instances
to/from JSON for the React frontend.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Classroom, ClassroomMembership
from accounts.serializers import UserProfileSerializer   # reuse existing safe user display

User = get_user_model()   # = accounts.User


# =============================================================================
# 1. CLASSROOM LIST SERIALIZER
#    Lightweight — used when listing many classrooms.
#    Does NOT include the full student list (would be too much data).
# =============================================================================

class ClassroomListSerializer(serializers.ModelSerializer):
    """
    Compact classroom representation for list views.
    Shows teacher's name and student count instead of full details.
    """

    # SerializerMethodField lets us compute a value with a custom method
    teacher_name = serializers.SerializerMethodField(
        help_text="Full name or username of the teacher who owns this classroom."
    )
    # WHY no 'source' here?
    # DRF raises AssertionError if source == field name (it's redundant).
    # 'student_count' maps automatically to the @property on the model.
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Classroom
        fields = [
            'id',
            'name',
            'description',
            'join_code',          # shown to teachers; students need it to join
            'teacher_name',       # computed field
            'student_count',      # computed property from model
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'join_code', 'teacher_name', 'student_count', 'created_at']

    def get_teacher_name(self, obj):
        """
        Return the teacher's full name if available, otherwise their username.
        'obj' is the Classroom instance being serialized.
        """
        teacher = obj.teacher
        full_name = f"{teacher.first_name} {teacher.last_name}".strip()
        return full_name if full_name else teacher.username


# =============================================================================
# 2. CLASSROOM DETAIL SERIALIZER
#    Full details — used when viewing a single classroom.
#    Includes nested teacher info and list of students.
# =============================================================================

class ClassroomDetailSerializer(serializers.ModelSerializer):
    """
    Full classroom data including nested teacher and student objects.
    Used for the GET /classrooms/<id>/ endpoint.
    """

    # Nest the full teacher profile (read-only — teacher is set by the view, not the user)
    teacher = UserProfileSerializer(read_only=True)

    # List of all students in this classroom, each as a full profile
    students = UserProfileSerializer(many=True, read_only=True)

    # WHY no 'source' here? Same reason as ClassroomListSerializer above:
    # DRF raises AssertionError when source matches field name exactly.
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Classroom
        fields = [
            'id',
            'name',
            'description',
            'join_code',
            'teacher',           # nested teacher object
            'students',          # list of nested student objects
            'student_count',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'join_code', 'teacher', 'students', 'student_count', 'created_at', 'updated_at']


# =============================================================================
# 3. CLASSROOM CREATE / UPDATE SERIALIZER
#    Used for POST (create) and PUT/PATCH (update) classroom requests.
#    Only accepts: name, description, is_active.
#    join_code and teacher are set automatically — not by the user.
# =============================================================================

class ClassroomWriteSerializer(serializers.ModelSerializer):
    """
    Accepts classroom data from a teacher to create or update a classroom.
    The 'teacher' field is NOT here — it is set in the view from request.user.
    The 'join_code' is NOT here — it is auto-generated in the model's save().
    """

    class Meta:
        model = Classroom
        fields = [
            'name',           # required
            'description',    # optional
            'is_active',      # optional (defaults to True)
        ]

    def validate_name(self, value):
        """
        Classroom name must not be empty or just whitespace.
        """
        if not value.strip():
            raise serializers.ValidationError("Classroom name cannot be blank.")
        return value.strip()   # remove leading/trailing spaces before saving


# =============================================================================
# 4. JOIN CLASSROOM SERIALIZER
#    Accepts the join code that the student submits.
# =============================================================================

class JoinClassroomSerializer(serializers.Serializer):
    """
    Accepts a join_code string from a student who wants to join a classroom.

    Why not use ModelSerializer here?
      We're not creating a Classroom — we're looking one up by code
      and then creating a ClassroomMembership. A plain Serializer is cleaner.
    """

    join_code = serializers.CharField(
        max_length=10,
        min_length=6,
        help_text="The unique join code for the classroom.",
        error_messages={
            'blank': 'Please enter a join code.',
            'max_length': 'Join code is too long.',
        }
    )

    def validate_join_code(self, value):
        """
        Check that a classroom with this code exists AND is active.
        If valid, we store the classroom on the serializer so the view can use it.
        """
        code = value.strip().upper()   # normalize — make uppercase, trim spaces

        try:
            classroom = Classroom.objects.get(join_code=code)
        except Classroom.DoesNotExist:
            raise serializers.ValidationError(
                "No classroom found with this join code. Please check and try again."
            )

        if not classroom.is_active:
            raise serializers.ValidationError(
                "This classroom is no longer active and is not accepting new students."
            )

        # Store the found classroom so the view can access it without another DB query
        self.context['classroom'] = classroom
        return code


# =============================================================================
# 5. CLASSROOM MEMBERSHIP SERIALIZER
#    Shows a membership record (student + classroom + join date).
# =============================================================================

class ClassroomMembershipSerializer(serializers.ModelSerializer):
    """
    Read-only display of a student's classroom membership.
    """
    student = UserProfileSerializer(read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    classroom_id = serializers.IntegerField(source='classroom.id', read_only=True)

    class Meta:
        model = ClassroomMembership
        fields = ['id', 'student', 'classroom_id', 'classroom_name', 'joined_at']
        read_only_fields = fields
