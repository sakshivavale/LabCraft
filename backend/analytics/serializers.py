"""
analytics/serializers.py

Serializers for LabCraft Analytics & Reporting Module.

These serializers validate and document the data contracts returned by the analytics
endpoints for both student and teacher dashboards.
"""

from rest_framework import serializers


class StatusDistributionSerializer(serializers.Serializer):
    """Breakdown of submission outcomes (accepted, wrong_answer, etc.)."""
    accepted = serializers.IntegerField(default=0)
    wrong_answer = serializers.IntegerField(default=0)
    compile_error = serializers.IntegerField(default=0)
    runtime_error = serializers.IntegerField(default=0)
    time_limit_exceeded = serializers.IntegerField(default=0)
    memory_limit_exceeded = serializers.IntegerField(default=0)
    pending = serializers.IntegerField(default=0)
    running = serializers.IntegerField(default=0)


class StudentSummarySerializer(serializers.Serializer):
    """High-level metrics for a student's platform activity."""
    enrolled_classrooms_count = serializers.IntegerField()
    total_assignments_available = serializers.IntegerField()
    assignments_submitted = serializers.IntegerField()
    assignments_pending = serializers.IntegerField()
    total_submissions = serializers.IntegerField()
    accepted_submissions = serializers.IntegerField()
    acceptance_rate = serializers.FloatField()
    total_score_earned = serializers.FloatField()
    total_possible_marks = serializers.IntegerField()
    overall_average_score_percentage = serializers.FloatField()


class StudentAssignmentBreakdownSerializer(serializers.Serializer):
    """Detailed assignment progress for a student."""
    assignment_id = serializers.IntegerField()
    assignment_title = serializers.CharField()
    classroom_id = serializers.IntegerField()
    classroom_name = serializers.CharField()
    due_date = serializers.DateTimeField(allow_null=True)
    max_marks = serializers.IntegerField()
    status = serializers.CharField()
    submitted = serializers.BooleanField()
    attempts_count = serializers.IntegerField()
    best_score = serializers.FloatField(allow_null=True)
    latest_status = serializers.CharField(allow_null=True)
    is_late = serializers.BooleanField(allow_null=True)


class StudentDashboardSerializer(serializers.Serializer):
    """Full response schema for GET /api/analytics/student/dashboard/."""
    summary = StudentSummarySerializer()
    status_distribution = StatusDistributionSerializer()
    recent_submissions = serializers.ListField(child=serializers.DictField())
    per_assignment_breakdown = serializers.ListField(child=StudentAssignmentBreakdownSerializer())


class TeacherSummarySerializer(serializers.Serializer):
    """High-level metrics for an instructor's platform activity."""
    total_classrooms = serializers.IntegerField()
    total_students_enrolled = serializers.IntegerField()
    total_assignments = serializers.IntegerField()
    published_assignments = serializers.IntegerField()
    total_submissions_received = serializers.IntegerField()
    overall_acceptance_rate = serializers.FloatField()


class TeacherDashboardSerializer(serializers.Serializer):
    """Full response schema for GET /api/analytics/teacher/dashboard/."""
    summary = TeacherSummarySerializer()
    status_distribution = StatusDistributionSerializer()
    classrooms_overview = serializers.ListField(child=serializers.DictField())
    recent_submissions = serializers.ListField(child=serializers.DictField())


class ClassroomAnalyticsSerializer(serializers.Serializer):
    """Full response schema for GET /api/analytics/classroom/<id>/."""
    classroom = serializers.DictField()
    metrics = serializers.DictField()
    status_distribution = StatusDistributionSerializer()
    assignments_breakdown = serializers.ListField(child=serializers.DictField())
    leaderboard = serializers.ListField(child=serializers.DictField())


class AssignmentAnalyticsSerializer(serializers.Serializer):
    """Full response schema for GET /api/analytics/assignment/<id>/."""
    assignment = serializers.DictField()
    metrics = serializers.DictField()
    status_distribution = StatusDistributionSerializer()
    score_distribution = serializers.DictField()
    student_gradebook = serializers.ListField(child=serializers.DictField())
