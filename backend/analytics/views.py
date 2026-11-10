"""
analytics/views.py

API Views for LabCraft Analytics & Performance Dashboard Module.

Endpoints Provided:
  1. GET /api/analytics/student/dashboard/
     - Student performance metrics, acceptance rate, per-assignment status.
  2. GET /api/analytics/teacher/dashboard/
     - Instructor-level summary across all owned classrooms.
  3. GET /api/analytics/classroom/<classroom_id>/
     - Detailed classroom analytics, student leaderboard, and pass rates.
  4. GET /api/analytics/assignment/<assignment_id>/
     - Assignment outcome distribution, score buckets, and student gradebook.
"""

from decimal import Decimal
from django.db.models import Count, Avg, Max, Min, Sum, Q
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from accounts.permissions import IsStudent, IsApprovedTeacher
from classrooms.models import Classroom, ClassroomMembership
from assignments.models import Assignment
from submissions.models import Submission
from grader.models import GradingResult


# Helper for consistent status distribution dictionary
def build_status_distribution(queryset):
    """
    Computes count for each submission status using a single aggregated SQL query.
    Prevents running separate COUNT queries for each status.
    """
    counts = queryset.aggregate(
        accepted=Count('id', filter=Q(status='accepted')),
        wrong_answer=Count('id', filter=Q(status='wrong_answer')),
        compile_error=Count('id', filter=Q(status='compile_error')),
        runtime_error=Count('id', filter=Q(status='runtime_error')),
        time_limit_exceeded=Count('id', filter=Q(status='time_limit_exceeded')),
        memory_limit_exceeded=Count('id', filter=Q(status='memory_limit_exceeded')),
        pending=Count('id', filter=Q(status='pending')),
        running=Count('id', filter=Q(status='running')),
    )
    return {k: counts[k] or 0 for k in counts}


# =============================================================================
# 1. STUDENT DASHBOARD ANALYTICS
# =============================================================================

class StudentDashboardAnalyticsView(APIView):
    """
    GET /api/analytics/student/dashboard/
    Provides an aggregated progress report for the authenticated student.
    """
    permission_classes = [IsStudent]

    def get(self, request):
        user = request.user

        # 1. Enrolled active classrooms
        memberships = ClassroomMembership.objects.filter(
            student=user,
            classroom__is_active=True
        ).select_related('classroom', 'classroom__teacher')

        enrolled_classrooms = [m.classroom for m in memberships]
        enrolled_classrooms_count = len(enrolled_classrooms)

        # 2. Available published assignments across student's classrooms
        available_assignments = Assignment.objects.filter(
            classroom__in=enrolled_classrooms,
            is_published=True
        ).select_related('classroom').order_by('-created_at')

        total_assignments_available = available_assignments.count()

        # 3. All submissions made by this student
        student_submissions = Submission.objects.filter(
            student=user
        ).select_related('assignment', 'assignment__classroom', 'grading_result').order_by('-submitted_at')

        total_submissions = student_submissions.count()
        accepted_submissions = student_submissions.filter(status='accepted').count()

        acceptance_rate = round(
            (accepted_submissions / total_submissions * 100.0), 2
        ) if total_submissions > 0 else 0.0

        # Group submissions by assignment_id in memory to avoid repeated DB hits
        submissions_by_assignment = {}
        for sub in student_submissions:
            submissions_by_assignment.setdefault(sub.assignment_id, []).append(sub)

        # 4. Detailed Per-Assignment Breakdown
        per_assignment_breakdown = []
        total_score_earned = 0.0
        total_possible_marks = 0

        for assignment in available_assignments:
            subs = submissions_by_assignment.get(assignment.id, [])
            has_submitted = len(subs) > 0
            total_possible_marks += assignment.max_marks

            best_score = None
            latest_status = None
            is_late = None

            if has_submitted:
                latest_sub = subs[0]  # sorted by -submitted_at
                latest_status = latest_sub.status
                is_late = latest_sub.is_late

                # Find highest score among attempts
                scores = [
                    float(s.grading_result.score)
                    for s in subs
                    if hasattr(s, 'grading_result') and s.grading_result and s.grading_result.score is not None
                ]
                if scores:
                    best_score = max(scores)
                    total_score_earned += best_score

            per_assignment_breakdown.append({
                'assignment_id': assignment.id,
                'assignment_title': assignment.title,
                'classroom_id': assignment.classroom.id,
                'classroom_name': assignment.classroom.name,
                'due_date': assignment.due_date,
                'max_marks': assignment.max_marks,
                'status': assignment.status,
                'submitted': has_submitted,
                'attempts_count': len(subs),
                'best_score': best_score,
                'latest_status': latest_status,
                'is_late': is_late,
            })

        assignments_submitted_count = sum(1 for item in per_assignment_breakdown if item['submitted'])
        assignments_pending_count = max(0, total_assignments_available - assignments_submitted_count)

        overall_avg_pct = round(
            (total_score_earned / total_possible_marks * 100.0), 2
        ) if total_possible_marks > 0 else 0.0

        # 5. Status distribution for this student
        status_distribution = build_status_distribution(student_submissions)

        # 6. Recent 5 submissions
        recent_submissions = [
            {
                'id': sub.id,
                'assignment_id': sub.assignment.id,
                'assignment_title': sub.assignment.title,
                'classroom_name': sub.assignment.classroom.name,
                'language': sub.language,
                'status': sub.status,
                'score': float(sub.grading_result.score) if hasattr(sub, 'grading_result') and sub.grading_result else None,
                'submitted_at': sub.submitted_at,
                'is_late': sub.is_late,
            }
            for sub in student_submissions[:5]
        ]

        # 7. Classroom summary
        classrooms_data = []
        for cr in enrolled_classrooms:
            cr_assignments = [a for a in available_assignments if a.classroom_id == cr.id]
            cr_assign_ids = {a.id for a in cr_assignments}
            cr_subs = [s for s in student_submissions if s.assignment_id in cr_assign_ids]

            cr_completed = len({s.assignment_id for s in cr_subs if s.status == 'accepted'})
            cr_marks = sum(
                max([float(s.grading_result.score) for s in cr_subs if s.assignment_id == a.id and hasattr(s, 'grading_result') and s.grading_result] or [0.0])
                for a in cr_assignments
            )
            cr_max_possible = sum(a.max_marks for a in cr_assignments)

            classrooms_data.append({
                'classroom_id': cr.id,
                'classroom_name': cr.name,
                'teacher_name': cr.teacher.get_full_name() or cr.teacher.username,
                'total_assignments': len(cr_assignments),
                'submitted_assignments': len({s.assignment_id for s in cr_subs}),
                'completed_assignments': cr_completed,
                'total_marks_earned': round(cr_marks, 2),
                'max_marks_possible': cr_max_possible,
            })

        return Response({
            'summary': {
                'enrolled_classrooms_count': enrolled_classrooms_count,
                'total_assignments_available': total_assignments_available,
                'assignments_submitted': assignments_submitted_count,
                'assignments_pending': assignments_pending_count,
                'total_submissions': total_submissions,
                'accepted_submissions': accepted_submissions,
                'acceptance_rate': acceptance_rate,
                'total_score_earned': round(total_score_earned, 2),
                'total_possible_marks': total_possible_marks,
                'overall_average_score_percentage': overall_avg_pct,
            },
            'status_distribution': status_distribution,
            'classrooms': classrooms_data,
            'recent_submissions': recent_submissions,
            'per_assignment_breakdown': per_assignment_breakdown,
        }, status=status.HTTP_200_OK)


# =============================================================================
# 2. TEACHER DASHBOARD ANALYTICS
# =============================================================================

class TeacherDashboardAnalyticsView(APIView):
    """
    GET /api/analytics/teacher/dashboard/
    Overview of all classrooms, student counts, and submissions for an approved teacher.
    """
    permission_classes = [IsApprovedTeacher]

    def get(self, request):
        teacher = request.user

        # All classrooms owned by this teacher
        classrooms = Classroom.objects.filter(teacher=teacher).order_by('-created_at')
        total_classrooms = classrooms.count()

        # Total unique students across all teacher's classrooms
        total_students_enrolled = ClassroomMembership.objects.filter(
            classroom__in=classrooms
        ).values('student').distinct().count()

        # Assignments created by teacher
        teacher_assignments = Assignment.objects.filter(classroom__teacher=teacher)
        total_assignments = teacher_assignments.count()
        published_assignments = teacher_assignments.filter(is_published=True).count()

        # Submissions across all teacher's assignments
        teacher_submissions = Submission.objects.filter(
            assignment__classroom__in=classrooms
        ).select_related('student', 'assignment', 'assignment__classroom', 'grading_result')

        total_submissions_received = teacher_submissions.count()
        accepted_submissions = teacher_submissions.filter(status='accepted').count()

        overall_acceptance_rate = round(
            (accepted_submissions / total_submissions_received * 100.0), 2
        ) if total_submissions_received > 0 else 0.0

        # Status distribution
        status_distribution = build_status_distribution(teacher_submissions)

        # Classroom overview cards
        classrooms_overview = []
        for cr in classrooms:
            cr_student_count = cr.memberships.count()
            cr_assign_count = cr.assignments.count()
            cr_subs = teacher_submissions.filter(assignment__classroom=cr)
            cr_sub_count = cr_subs.count()

            # Average score calculation using GradingResult
            avg_score_data = GradingResult.objects.filter(
                submission__assignment__classroom=cr
            ).aggregate(avg_score=Avg('score'))

            avg_score = round(float(avg_score_data['avg_score']), 2) if avg_score_data['avg_score'] is not None else 0.0

            classrooms_overview.append({
                'id': cr.id,
                'name': cr.name,
                'join_code': cr.join_code,
                'is_active': cr.is_active,
                'student_count': cr_student_count,
                'total_assignments': cr_assign_count,
                'total_submissions': cr_sub_count,
                'average_score': avg_score,
            })

        # Recent 10 submissions across all teacher classrooms
        recent_subs_qs = teacher_submissions.order_by('-submitted_at')[:10]
        recent_submissions = [
            {
                'id': s.id,
                'assignment_id': s.assignment.id,
                'assignment_title': s.assignment.title,
                'classroom_id': s.assignment.classroom.id,
                'classroom_name': s.assignment.classroom.name,
                'student_username': s.student.username,
                'status': s.status,
                'score': float(s.grading_result.score) if hasattr(s, 'grading_result') and s.grading_result else None,
                'submitted_at': s.submitted_at,
                'is_late': s.is_late,
            }
            for s in recent_subs_qs
        ]

        return Response({
            'summary': {
                'total_classrooms': total_classrooms,
                'total_students_enrolled': total_students_enrolled,
                'total_assignments': total_assignments,
                'published_assignments': published_assignments,
                'total_submissions_received': total_submissions_received,
                'overall_acceptance_rate': overall_acceptance_rate,
            },
            'status_distribution': status_distribution,
            'classrooms_overview': classrooms_overview,
            'recent_submissions': recent_submissions,
        }, status=status.HTTP_200_OK)


# =============================================================================
# 3. CLASSROOM ANALYTICS & LEADERBOARD
# =============================================================================

class ClassroomAnalyticsView(APIView):
    """
    GET /api/analytics/classroom/<classroom_id>/
    Deep-dive metrics, pass rates, and gradebook leaderboard for a specific classroom.
    """
    permission_classes = [IsApprovedTeacher]

    def get(self, request, classroom_id):
        # Security: Classroom must belong to the logged-in approved teacher
        classroom = get_object_or_404(
            Classroom,
            id=classroom_id,
            teacher=request.user
        )

        memberships = classroom.memberships.select_related('student')
        enrolled_students = [m.student for m in memberships]
        enrolled_students_count = len(enrolled_students)

        assignments = classroom.assignments.all().order_by('-created_at')
        total_assignments = assignments.count()
        published_assignments = assignments.filter(is_published=True).count()

        classroom_submissions = Submission.objects.filter(
            assignment__classroom=classroom
        ).select_related('student', 'assignment', 'grading_result')

        total_submissions = classroom_submissions.count()
        unique_students_submitted = classroom_submissions.values('student').distinct().count()

        submission_rate = round(
            (unique_students_submitted / enrolled_students_count * 100.0), 2
        ) if enrolled_students_count > 0 else 0.0

        avg_score_data = GradingResult.objects.filter(
            submission__assignment__classroom=classroom
        ).aggregate(avg_score=Avg('score'))

        average_classroom_score = round(
            float(avg_score_data['avg_score']), 2
        ) if avg_score_data['avg_score'] is not None else 0.0

        status_distribution = build_status_distribution(classroom_submissions)

        # Assignments breakdown
        assignments_breakdown = []
        for assign in assignments:
            assign_subs = classroom_submissions.filter(assignment=assign)
            assign_total_subs = assign_subs.count()
            assign_unique_students = assign_subs.values('student').distinct().count()

            # Students who achieved 'accepted' on this assignment
            accepted_students_count = assign_subs.filter(status='accepted').values('student').distinct().count()

            pass_rate = round(
                (accepted_students_count / enrolled_students_count * 100.0), 2
            ) if enrolled_students_count > 0 else 0.0

            assign_avg_data = GradingResult.objects.filter(
                submission__assignment=assign
            ).aggregate(avg_score=Avg('score'))
            assign_avg = round(float(assign_avg_data['avg_score']), 2) if assign_avg_data['avg_score'] is not None else 0.0

            assignments_breakdown.append({
                'id': assign.id,
                'title': assign.title,
                'max_marks': assign.max_marks,
                'is_published': assign.is_published,
                'status': assign.status,
                'total_submissions': assign_total_subs,
                'unique_students_submitted': assign_unique_students,
                'passed_students_count': accepted_students_count,
                'pass_rate': pass_rate,
                'average_score': assign_avg,
            })

        # Student Leaderboard / Gradebook
        # Pre-group submissions by student_id
        subs_by_student = {}
        for sub in classroom_submissions:
            subs_by_student.setdefault(sub.student_id, []).append(sub)

        leaderboard = []
        for student in enrolled_students:
            s_subs = subs_by_student.get(student.id, [])

            # Number of assignments where student got accepted
            completed_assignments = len({s.assignment_id for s in s_subs if s.status == 'accepted'})

            # Best score per assignment
            total_earned = 0.0
            for assign in assignments:
                assign_student_subs = [s for s in s_subs if s.assignment_id == assign.id]
                scores = [
                    float(s.grading_result.score)
                    for s in assign_student_subs
                    if hasattr(s, 'grading_result') and s.grading_result and s.grading_result.score is not None
                ]
                if scores:
                    total_earned += max(scores)

            leaderboard.append({
                'student_id': student.id,
                'username': student.username,
                'full_name': student.get_full_name() or student.username,
                'email': student.email,
                'assignments_completed': completed_assignments,
                'total_score': round(total_earned, 2),
                'submission_count': len(s_subs),
            })

        # Rank students by total score descending, then completed count descending
        leaderboard.sort(key=lambda x: (x['total_score'], x['assignments_completed']), reverse=True)

        return Response({
            'classroom': {
                'id': classroom.id,
                'name': classroom.name,
                'join_code': classroom.join_code,
                'created_at': classroom.created_at,
                'is_active': classroom.is_active,
            },
            'metrics': {
                'enrolled_students_count': enrolled_students_count,
                'total_assignments': total_assignments,
                'published_assignments': published_assignments,
                'total_submissions': total_submissions,
                'unique_students_submitted': unique_students_submitted,
                'submission_rate': submission_rate,
                'average_classroom_score': average_classroom_score,
            },
            'status_distribution': status_distribution,
            'assignments_breakdown': assignments_breakdown,
            'leaderboard': leaderboard,
        }, status=status.HTTP_200_OK)


# =============================================================================
# 4. ASSIGNMENT ANALYTICS & GRADEBOOK
# =============================================================================

class AssignmentAnalyticsView(APIView):
    """
    GET /api/analytics/assignment/<assignment_id>/
    Deep-dive outcome analysis, score distribution buckets, and student gradebook for an assignment.
    """
    permission_classes = [IsApprovedTeacher]

    def get(self, request, assignment_id):
        # Security: Assignment must belong to a classroom owned by this teacher
        assignment = get_object_or_404(
            Assignment,
            id=assignment_id,
            classroom__teacher=request.user
        )

        classroom = assignment.classroom
        memberships = classroom.memberships.select_related('student')
        enrolled_students = [m.student for m in memberships]
        total_enrolled_students = len(enrolled_students)

        submissions = assignment.submissions.select_related('student', 'grading_result').order_by('-submitted_at')
        total_submissions = submissions.count()

        students_submitted_set = {s.student_id for s in submissions}
        students_submitted_count = len(students_submitted_set)
        students_not_submitted_count = max(0, total_enrolled_students - students_submitted_count)

        submission_rate = round(
            (students_submitted_count / total_enrolled_students * 100.0), 2
        ) if total_enrolled_students > 0 else 0.0

        students_accepted_count = len({s.student_id for s in submissions if s.status == 'accepted'})
        pass_rate = round(
            (students_accepted_count / total_enrolled_students * 100.0), 2
        ) if total_enrolled_students > 0 else 0.0

        # Score stats
        score_stats = GradingResult.objects.filter(
            submission__assignment=assignment
        ).aggregate(
            avg_score=Avg('score'),
            max_score=Max('score'),
            min_score=Min('score'),
        )

        average_score = round(float(score_stats['avg_score']), 2) if score_stats['avg_score'] is not None else 0.0
        highest_score = float(score_stats['max_score']) if score_stats['max_score'] is not None else 0.0
        lowest_score = float(score_stats['min_score']) if score_stats['min_score'] is not None else 0.0

        status_distribution = build_status_distribution(submissions)

        # Score distribution buckets (0-20%, 21-40%, 41-60%, 61-80%, 81-100%)
        score_distribution = {
            '0_to_20_pct': 0,
            '21_to_40_pct': 0,
            '41_to_60_pct': 0,
            '61_to_80_pct': 0,
            '81_to_100_pct': 0,
        }

        # Collect best score per student who submitted
        subs_by_student = {}
        for s in submissions:
            subs_by_student.setdefault(s.student_id, []).append(s)

        for s_id, s_list in subs_by_student.items():
            scores = [
                float(s.grading_result.score)
                for s in s_list
                if hasattr(s, 'grading_result') and s.grading_result and s.grading_result.score is not None
            ]
            if scores:
                best = max(scores)
                pct = (best / assignment.max_marks * 100.0) if assignment.max_marks > 0 else 0.0
                if pct <= 20:
                    score_distribution['0_to_20_pct'] += 1
                elif pct <= 40:
                    score_distribution['21_to_40_pct'] += 1
                elif pct <= 60:
                    score_distribution['41_to_60_pct'] += 1
                elif pct <= 80:
                    score_distribution['61_to_80_pct'] += 1
                else:
                    score_distribution['81_to_100_pct'] += 1

        # Student Gradebook
        student_gradebook = []
        for student in enrolled_students:
            s_list = subs_by_student.get(student.id, [])
            has_submitted = len(s_list) > 0

            best_score = None
            latest_status = None
            is_late = None
            latest_time = None

            if has_submitted:
                latest_sub = s_list[0]
                latest_status = latest_sub.status
                is_late = latest_sub.is_late
                latest_time = latest_sub.submitted_at

                scores = [
                    float(s.grading_result.score)
                    for s in s_list
                    if hasattr(s, 'grading_result') and s.grading_result and s.grading_result.score is not None
                ]
                if scores:
                    best_score = max(scores)

            student_gradebook.append({
                'student_id': student.id,
                'username': student.username,
                'full_name': student.get_full_name() or student.username,
                'submitted': has_submitted,
                'attempts_count': len(s_list),
                'best_score': best_score,
                'latest_status': latest_status,
                'is_late': is_late,
                'latest_submission_time': latest_time,
            })

        # Order gradebook: submitted first, then by best score descending
        student_gradebook.sort(
            key=lambda x: (x['submitted'], x['best_score'] if x['best_score'] is not None else -1),
            reverse=True
        )

        return Response({
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'classroom_id': classroom.id,
                'classroom_name': classroom.name,
                'due_date': assignment.due_date,
                'max_marks': assignment.max_marks,
                'language': assignment.language,
                'difficulty': assignment.difficulty,
                'is_published': assignment.is_published,
                'status': assignment.status,
            },
            'metrics': {
                'total_enrolled_students': total_enrolled_students,
                'total_submissions': total_submissions,
                'students_submitted': students_submitted_count,
                'students_not_submitted': students_not_submitted_count,
                'submission_rate': submission_rate,
                'students_accepted': students_accepted_count,
                'pass_rate': pass_rate,
                'average_score': average_score,
                'highest_score': highest_score,
                'lowest_score': lowest_score,
            },
            'status_distribution': status_distribution,
            'score_distribution': score_distribution,
            'student_gradebook': student_gradebook,
        }, status=status.HTTP_200_OK)
