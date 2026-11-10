"""
analytics/tests.py

Comprehensive Test Suite for LabCraft Analytics Dashboard (Module 6).

Test Classes:
  1. StudentDashboardAnalyticsTest  — Tests student metrics, acceptance rate, per-assignment status.
  2. TeacherDashboardAnalyticsTest  — Tests multi-classroom overview, student counts, average scores.
  3. ClassroomAnalyticsTest         — Tests classroom metrics, assignment breakdown, student leaderboard.
  4. AssignmentAnalyticsTest        — Tests outcome distribution, score buckets, and gradebook.
  5. AnalyticsPermissionTest        — Tests role-based permissions, cross-teacher isolation, 401/403/404.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from classrooms.models import Classroom, ClassroomMembership
from assignments.models import Assignment
from submissions.models import Submission
from grader.models import GradingResult

User = get_user_model()


def make_student(username, email=None):
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@test.com",
        password="Pass123!Secure",
        role=User.Role.STUDENT,
        is_approved=True
    )


def make_teacher(username, email=None, approved=True):
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@test.com",
        password="Pass123!Secure",
        role=User.Role.TEACHER,
        is_approved=approved
    )


def make_classroom(teacher, name="Data Structures Lab"):
    return Classroom.objects.create(teacher=teacher, name=name)


def enroll(student, classroom):
    return ClassroomMembership.objects.create(student=student, classroom=classroom)


def make_assignment(classroom, teacher, title="Stack Implementation", max_marks=100, published=True):
    return Assignment.objects.create(
        classroom=classroom,
        created_by=teacher,
        title=title,
        max_marks=max_marks,
        is_published=published
    )


def make_submission(assignment, student, sub_status="accepted", code="print(1)"):
    sub = Submission.objects.create(
        assignment=assignment,
        student=student,
        source_code=code,
        language="python",
        status=sub_status
    )
    return sub


def make_grading_result(submission, score=100.00, res_status="accepted", total=2, passed=2):
    return GradingResult.objects.create(
        submission=submission,
        status=res_status,
        total_count=total,
        passed_count=passed,
        score=Decimal(str(score)),
        execution_log=[]
    )


# =============================================================================
# 1. STUDENT DASHBOARD TESTS
# =============================================================================

class StudentDashboardAnalyticsTest(APITestCase):
    """Tests for GET /api/analytics/student/dashboard/"""

    def setUp(self):
        self.teacher = make_teacher("dash_teacher")
        self.student = make_student("dash_student")
        self.classroom = make_classroom(self.teacher, "Python Lab")
        enroll(self.student, self.classroom)

        # 2 published assignments
        self.a1 = make_assignment(self.classroom, self.teacher, "Lab 1", max_marks=100)
        self.a2 = make_assignment(self.classroom, self.teacher, "Lab 2", max_marks=50)

        # Submissions: A1 has 1 accepted; A2 has 1 wrong_answer
        sub1 = make_submission(self.a1, self.student, "accepted")
        make_grading_result(sub1, score=100.00, res_status="accepted")

        sub2 = make_submission(self.a2, self.student, "wrong_answer")
        make_grading_result(sub2, score=25.00, res_status="wrong_answer")

        self.url = reverse('student-analytics-dashboard')

    def test_student_dashboard_metrics(self):
        """Student dashboard returns aggregated summary, rate, and breakdown."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        summary = response.data['summary']

        self.assertEqual(summary['enrolled_classrooms_count'], 1)
        self.assertEqual(summary['total_assignments_available'], 2)
        self.assertEqual(summary['assignments_submitted'], 2)
        self.assertEqual(summary['assignments_pending'], 0)
        self.assertEqual(summary['total_submissions'], 2)
        self.assertEqual(summary['accepted_submissions'], 1)
        self.assertEqual(summary['acceptance_rate'], 50.0)
        self.assertEqual(summary['total_score_earned'], 125.0)  # 100 + 25
        self.assertEqual(summary['total_possible_marks'], 150)  # 100 + 50

        # Status distribution check
        dist = response.data['status_distribution']
        self.assertEqual(dist['accepted'], 1)
        self.assertEqual(dist['wrong_answer'], 1)

        # Per assignment breakdown
        breakdown = response.data['per_assignment_breakdown']
        self.assertEqual(len(breakdown), 2)
        a1_item = next(b for b in breakdown if b['assignment_id'] == self.a1.id)
        self.assertTrue(a1_item['submitted'])
        self.assertEqual(a1_item['best_score'], 100.0)
        self.assertEqual(a1_item['latest_status'], 'accepted')

    def test_student_with_zero_classrooms_or_submissions(self):
        """New student with no enrolled classrooms or submissions returns zero metrics safely."""
        new_student = make_student("empty_student")
        self.client.force_authenticate(user=new_student)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        summary = response.data['summary']
        self.assertEqual(summary['enrolled_classrooms_count'], 0)
        self.assertEqual(summary['total_assignments_available'], 0)
        self.assertEqual(summary['total_submissions'], 0)
        self.assertEqual(summary['acceptance_rate'], 0.0)


# =============================================================================
# 2. TEACHER DASHBOARD TESTS
# =============================================================================

class TeacherDashboardAnalyticsTest(APITestCase):
    """Tests for GET /api/analytics/teacher/dashboard/"""

    def setUp(self):
        self.teacher = make_teacher("prof_analytics")
        self.student1 = make_student("stud1")
        self.student2 = make_student("stud2")

        # 2 classrooms
        self.c1 = make_classroom(self.teacher, "Class 1")
        self.c2 = make_classroom(self.teacher, "Class 2")

        enroll(self.student1, self.c1)
        enroll(self.student2, self.c1)
        enroll(self.student1, self.c2)  # student 1 is in both

        # Assignments
        self.a1 = make_assignment(self.c1, self.teacher, "Assignment 1", max_marks=100)
        self.a2 = make_assignment(self.c2, self.teacher, "Assignment 2", max_marks=100)

        # Submissions
        s1 = make_submission(self.a1, self.student1, "accepted")
        make_grading_result(s1, score=100.00)

        s2 = make_submission(self.a1, self.student2, "wrong_answer")
        make_grading_result(s2, score=50.00)

        self.url = reverse('teacher-analytics-dashboard')

    def test_teacher_dashboard_overview(self):
        """Teacher dashboard aggregates classrooms, unique students, and submissions."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        summary = response.data['summary']

        self.assertEqual(summary['total_classrooms'], 2)
        self.assertEqual(summary['total_students_enrolled'], 2)  # unique students
        self.assertEqual(summary['total_assignments'], 2)
        self.assertEqual(summary['total_submissions_received'], 2)
        self.assertEqual(summary['overall_acceptance_rate'], 50.0)

        # Classrooms overview
        c_list = response.data['classrooms_overview']
        self.assertEqual(len(c_list), 2)
        c1_item = next(c for c in c_list if c['id'] == self.c1.id)
        self.assertEqual(c1_item['student_count'], 2)
        self.assertEqual(c1_item['total_submissions'], 2)
        self.assertEqual(c1_item['average_score'], 75.0)  # (100 + 50) / 2

    def test_teacher_with_zero_classrooms(self):
        """Teacher with no classrooms returns zero metrics safely without error."""
        new_teacher = make_teacher("new_prof")
        self.client.force_authenticate(user=new_teacher)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['total_classrooms'], 0)
        self.assertEqual(response.data['summary']['total_submissions_received'], 0)


# =============================================================================
# 3. CLASSROOM ANALYTICS TESTS
# =============================================================================

class ClassroomAnalyticsTest(APITestCase):
    """Tests for GET /api/analytics/classroom/<classroom_id>/"""

    def setUp(self):
        self.teacher = make_teacher("cr_teacher")
        self.student_top = make_student("top_student")
        self.student_avg = make_student("avg_student")

        self.classroom = make_classroom(self.teacher, "Algorithms Lab")
        enroll(self.student_top, self.classroom)
        enroll(self.student_avg, self.classroom)

        self.a1 = make_assignment(self.classroom, self.teacher, "Sorting", max_marks=100)

        # Submissions
        s_top = make_submission(self.a1, self.student_top, "accepted")
        make_grading_result(s_top, score=100.00)

        s_avg = make_submission(self.a1, self.student_avg, "wrong_answer")
        make_grading_result(s_avg, score=60.00)

        self.url = reverse('classroom-analytics', kwargs={'classroom_id': self.classroom.id})

    def test_classroom_metrics_and_leaderboard(self):
        """Classroom endpoint returns submission rate, assignment stats, and ranked leaderboard."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = response.data['metrics']

        self.assertEqual(metrics['enrolled_students_count'], 2)
        self.assertEqual(metrics['total_assignments'], 1)
        self.assertEqual(metrics['total_submissions'], 2)
        self.assertEqual(metrics['unique_students_submitted'], 2)
        self.assertEqual(metrics['submission_rate'], 100.0)
        self.assertEqual(metrics['average_classroom_score'], 80.0)  # (100 + 60) / 2

        # Leaderboard ranking: top_student first, avg_student second
        board = response.data['leaderboard']
        self.assertEqual(len(board), 2)
        self.assertEqual(board[0]['username'], 'top_student')
        self.assertEqual(board[0]['total_score'], 100.0)
        self.assertEqual(board[0]['assignments_completed'], 1)

        self.assertEqual(board[1]['username'], 'avg_student')
        self.assertEqual(board[1]['total_score'], 60.0)
        self.assertEqual(board[1]['assignments_completed'], 0)


# =============================================================================
# 4. ASSIGNMENT ANALYTICS TESTS
# =============================================================================

class AssignmentAnalyticsTest(APITestCase):
    """Tests for GET /api/analytics/assignment/<assignment_id>/"""

    def setUp(self):
        self.teacher = make_teacher("assign_teacher")
        self.student1 = make_student("s1_assign")
        self.student2 = make_student("s2_assign")
        self.student_idle = make_student("s_idle")  # enrolled but no submission

        self.classroom = make_classroom(self.teacher, "OS Lab")
        enroll(self.student1, self.classroom)
        enroll(self.student2, self.classroom)
        enroll(self.student_idle, self.classroom)

        self.assignment = make_assignment(self.classroom, self.teacher, "Processes", max_marks=100)

        # student 1: 100 score
        s1 = make_submission(self.assignment, self.student1, "accepted")
        make_grading_result(s1, score=100.00)

        # student 2: 40 score
        s2 = make_submission(self.assignment, self.student2, "wrong_answer")
        make_grading_result(s2, score=40.00)

        self.url = reverse('assignment-analytics', kwargs={'assignment_id': self.assignment.id})

    def test_assignment_outcome_and_score_buckets(self):
        """Assignment analytics returns rates, highest/lowest scores, score distribution buckets."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = response.data['metrics']

        self.assertEqual(metrics['total_enrolled_students'], 3)
        self.assertEqual(metrics['total_submissions'], 2)
        self.assertEqual(metrics['students_submitted'], 2)
        self.assertEqual(metrics['students_not_submitted'], 1)  # student_idle
        self.assertEqual(metrics['submission_rate'], 66.67)     # 2/3 * 100
        self.assertEqual(metrics['students_accepted'], 1)
        self.assertEqual(metrics['pass_rate'], 33.33)           # 1/3 * 100
        self.assertEqual(metrics['highest_score'], 100.0)
        self.assertEqual(metrics['lowest_score'], 40.0)
        self.assertEqual(metrics['average_score'], 70.0)

        # Score buckets check: 40% in '21_to_40_pct', 100% in '81_to_100_pct'
        buckets = response.data['score_distribution']
        self.assertEqual(buckets['21_to_40_pct'], 1)
        self.assertEqual(buckets['81_to_100_pct'], 1)

        # Gradebook check: all 3 students included
        gradebook = response.data['student_gradebook']
        self.assertEqual(len(gradebook), 3)

        idle_entry = next(g for g in gradebook if g['username'] == 's_idle')
        self.assertFalse(idle_entry['submitted'])
        self.assertIsNone(idle_entry['best_score'])


# =============================================================================
# 5. PERMISSION & ACCESS CONTROL TESTS
# =============================================================================

class AnalyticsPermissionTest(APITestCase):
    """Verifies security isolation across all 4 analytics endpoints."""

    def setUp(self):
        self.teacher_a = make_teacher("teacher_a")
        self.teacher_b = make_teacher("teacher_b")
        self.student = make_student("student_p")
        self.pending_teacher = make_teacher("pending_t", approved=False)

        self.classroom_a = make_classroom(self.teacher_a, "Class A")
        self.assignment_a = make_assignment(self.classroom_a, self.teacher_a, "Assign A")

    def test_unauthenticated_requests_blocked(self):
        """Unauthenticated access returns 401 across all endpoints."""
        urls = [
            reverse('student-analytics-dashboard'),
            reverse('teacher-analytics-dashboard'),
            reverse('classroom-analytics', kwargs={'classroom_id': self.classroom_a.id}),
            reverse('assignment-analytics', kwargs={'assignment_id': self.assignment_a.id}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_access_teacher_endpoints(self):
        """Student receives 403 Forbidden on teacher analytics endpoints."""
        self.client.force_authenticate(user=self.student)

        teacher_urls = [
            reverse('teacher-analytics-dashboard'),
            reverse('classroom-analytics', kwargs={'classroom_id': self.classroom_a.id}),
            reverse('assignment-analytics', kwargs={'assignment_id': self.assignment_a.id}),
        ]
        for url in teacher_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_access_student_dashboard(self):
        """Teachers cannot access student dashboard (403 Forbidden)."""
        self.client.force_authenticate(user=self.teacher_a)
        response = self.client.get(reverse('student-analytics-dashboard'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_access_other_teachers_classroom_analytics(self):
        """Teacher B accessing Teacher A's classroom analytics gets 404 Not Found."""
        self.client.force_authenticate(user=self.teacher_b)
        url = reverse('classroom-analytics', kwargs={'classroom_id': self.classroom_a.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_access_other_teachers_assignment_analytics(self):
        """Teacher B accessing Teacher A's assignment analytics gets 404 Not Found."""
        self.client.force_authenticate(user=self.teacher_b)
        url = reverse('assignment-analytics', kwargs={'assignment_id': self.assignment_a.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pending_teacher_blocked(self):
        """Unapproved teacher receives 403 Forbidden on teacher endpoints."""
        self.client.force_authenticate(user=self.pending_teacher)
        response = self.client.get(reverse('teacher-analytics-dashboard'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
