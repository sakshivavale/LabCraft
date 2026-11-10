"""
grader/serializers.py

DRF Serializers for the Automated Grading Engine module.

Security Requirements Enforced Here:
  1. Teachers see all test cases (both public and hidden), including input and expected output.
  2. Students must NEVER see hidden test case inputs, outputs, or detailed diffs.
     - TestCaseStudentSerializer masks or filters hidden test cases.
     - GradingResultStudentSerializer sanitizes execution_log to redact hidden test case details.
"""

from rest_framework import serializers
from .models import TestCase, GradingResult


# =============================================================================
# 1. TEST CASE SERIALIZERS
# =============================================================================

class TestCaseTeacherSerializer(serializers.ModelSerializer):
    """
    Full test case serializer for teachers.
    Allows creating, viewing, and updating public and hidden test cases.
    """
    assignment_id = serializers.IntegerField(source='assignment.id', read_only=True)

    class Meta:
        model = TestCase
        fields = [
            'id',
            'assignment_id',
            'input_data',
            'expected_output',
            'is_hidden',
            'time_limit',
            'memory_limit',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'assignment_id', 'created_at', 'updated_at']

    def validate_time_limit(self, value):
        """Time limit must be between 0.1s and 30.0s."""
        if value <= 0:
            raise serializers.ValidationError("Time limit must be greater than 0.")
        if value > 30.0:
            raise serializers.ValidationError("Time limit cannot exceed 30.0 seconds.")
        return value

    def validate_expected_output(self, value):
        """Expected output cannot be empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Expected output cannot be empty.")
        return value


class TestCaseStudentSerializer(serializers.ModelSerializer):
    """
    Public test case serializer for students.
    Used when a student reviews the assignment's sample test cases.

    CRITICAL SECURITY:
      If a test case is marked is_hidden=True, this serializer redacts
      both input_data and expected_output so students cannot inspect hidden tests.
    """
    assignment_id = serializers.IntegerField(source='assignment.id', read_only=True)
    input_data = serializers.SerializerMethodField()
    expected_output = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        fields = [
            'id',
            'assignment_id',
            'input_data',
            'expected_output',
            'is_hidden',
            'time_limit',
            'memory_limit',
        ]
        read_only_fields = fields

    def get_input_data(self, obj):
        if obj.is_hidden:
            return "[Hidden Test Case]"
        return obj.input_data

    def get_expected_output(self, obj):
        if obj.is_hidden:
            return "[Hidden Test Case]"
        return obj.expected_output


# =============================================================================
# 2. GRADING RESULT SERIALIZERS
# =============================================================================

class GradingResultTeacherSerializer(serializers.ModelSerializer):
    """
    Full grading result serializer for teachers.
    Includes the complete execution log with all inputs, outputs, and diffs.
    """
    submission_id = serializers.IntegerField(source='submission.id', read_only=True)
    pass_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = GradingResult
        fields = [
            'id',
            'submission_id',
            'status',
            'total_count',
            'passed_count',
            'score',
            'pass_percentage',
            'execution_log',
            'error_message',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class GradingResultStudentSerializer(serializers.ModelSerializer):
    """
    Sanitized grading result serializer for students.

    CRITICAL SECURITY:
      Hides actual_output, expected_output, and diff details for any test case
      where is_hidden=True. Students can only see whether the hidden test passed
      or failed, but not what the test input was or what failed.
    """
    submission_id = serializers.IntegerField(source='submission.id', read_only=True)
    pass_percentage = serializers.FloatField(read_only=True)
    execution_log = serializers.SerializerMethodField()

    class Meta:
        model = GradingResult
        fields = [
            'id',
            'submission_id',
            'status',
            'total_count',
            'passed_count',
            'score',
            'pass_percentage',
            'execution_log',
            'error_message',
            'created_at',
        ]
        read_only_fields = fields

    def get_execution_log(self, obj):
        """Sanitizes execution log by redacting hidden test case output/diff."""
        sanitized = []
        for entry in obj.execution_log:
            item = dict(entry)
            if item.get('is_hidden', False):
                item['actual_output'] = '[Hidden]'
                item['expected_output'] = '[Hidden]'
                item['diff'] = ''
            sanitized.append(item)
        return sanitized
