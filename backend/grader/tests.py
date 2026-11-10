"""
grader/tests.py

Comprehensive Test Suite for the Automated Grading Engine (Module 5).

Test Classes:
  1. ComparatorTest               — Tests output normalization, CRLF handling, and diff generation.
  2. TestCaseModelTest            — Tests TestCase creation, visibility defaults, and validation.
  3. TestCaseAPITest              — Tests Teacher CRUD, student public view, and hidden test case protection.
  4. GradingEngineEvaluationTest  — Tests all outcome evaluations (AC, WA, CE, RE, TLE, MLE, Score calculation).
  5. DockerSafeFallbackTest       — Tests that engine fails safely when Docker daemon is unavailable.
  6. GradingResultAPITest         — Tests result endpoint, student masking of hidden tests, and teacher access.
  7. AsyncGradingQueueTest        — Tests background worker execution.
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

from .models import TestCase as AssignmentTestCase, GradingResult
from .comparator import normalize_output, compare_outputs
from .docker_engine import ExecutionResult, is_docker_available
from .engine import grade_submission
from .tasks import enqueue_grading

User = get_user_model()


# =============================================================================
# HELPER FACTORIES
# =============================================================================

def create_student(username, email=None):
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@test.com",
        password="TestPass123!",
        role=User.Role.STUDENT,
        is_approved=True
    )


def create_teacher(username, email=None):
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@test.com",
        password="TestPass123!",
        role=User.Role.TEACHER,
        is_approved=True
    )


def create_classroom(teacher, name="Grading Lab"):
    return Classroom.objects.create(teacher=teacher, name=name)


def create_assignment(classroom, teacher, title="Sum Two Numbers", max_marks=100, **kwargs):
    return Assignment.objects.create(
        classroom=classroom,
        created_by=teacher,
        title=title,
        max_marks=max_marks,
        is_published=True,
        **kwargs
    )


def create_test_case(assignment, input_data="2 3\n", expected_output="5\n", is_hidden=False, **kwargs):
    return AssignmentTestCase.objects.create(
        assignment=assignment,
        input_data=input_data,
        expected_output=expected_output,
        is_hidden=is_hidden,
        **kwargs
    )


def enroll_student(student, classroom):
    return ClassroomMembership.objects.create(student=student, classroom=classroom)


def create_submission(assignment, student, code="print(sum(map(int, input().split())))", language="python"):
    return Submission.objects.create(
        assignment=assignment,
        student=student,
        source_code=code,
        language=language,
        status=Submission.Status.PENDING
    )


# =============================================================================
# 1. COMPARATOR & NORMALIZATION TESTS
# =============================================================================

class ComparatorTest(TestCase):
    """Tests whitespace normalization and stdout comparison."""

    def test_normalize_output_handles_crlf_and_trailing_spaces(self):
        """CRLF and line trailing whitespace should be stripped."""
        raw = "42   \r\n84  \r\n\r\n"
        expected = "42\n84"
        self.assertEqual(normalize_output(raw), expected)

    def test_normalize_output_handles_empty_or_none(self):
        """None or empty string returns empty string."""
        self.assertEqual(normalize_output(None), "")
        self.assertEqual(normalize_output("   \n\n  "), "")

    def test_compare_outputs_matching(self):
        """Matching outputs return True and empty diff."""
        actual = "Hello World\n"
        expected = "Hello World  \r\n"
        matches, diff = compare_outputs(actual, expected)
        self.assertTrue(matches)
        self.assertEqual(diff, "")

    def test_compare_outputs_different(self):
        """Different outputs return False and unified diff."""
        actual = "Hello Python\n"
        expected = "Hello World\n"
        matches, diff = compare_outputs(actual, expected)
        self.assertFalse(matches)
        self.assertIn("Hello Python", diff)
        self.assertIn("Hello World", diff)


# =============================================================================
# 2. TEST CASE MODEL TESTS
# =============================================================================

class TestCaseModelTest(TestCase):
    """Tests for the TestCase database model."""

    def setUp(self):
        self.teacher = create_teacher("tc_teacher")
        self.classroom = create_classroom(self.teacher)
        self.assignment = create_assignment(self.classroom, self.teacher)

    def test_create_test_case_defaults(self):
        """Creating a TestCase sets default time limit and memory limit."""
        tc = create_test_case(self.assignment, "1\n", "2\n")
        self.assertEqual(tc.assignment, self.assignment)
        self.assertEqual(tc.input_data, "1\n")
        self.assertEqual(tc.expected_output, "2\n")
        self.assertFalse(tc.is_hidden)
        self.assertEqual(tc.time_limit, 2.0)
        self.assertEqual(tc.memory_limit, "128m")

    def test_str_representation(self):
        """__str__ indicates assignment title and visibility."""
        tc = create_test_case(self.assignment, is_hidden=True)
        self.assertIn("Hidden", str(tc))
        self.assertIn(self.assignment.title, str(tc))


# =============================================================================
# 3. TEST CASE API & SECURITY TESTS
# =============================================================================

class TestCaseAPITest(APITestCase):
    """Tests for TestCase REST API endpoints and student privacy protections."""

    def setUp(self):
        self.teacher = create_teacher("api_teacher")
        self.student = create_student("api_student")
        self.classroom = create_classroom(self.teacher)
        enroll_student(self.student, self.classroom)
        self.assignment = create_assignment(self.classroom, self.teacher)

        # 1 public test case, 1 hidden test case
        self.public_tc = create_test_case(self.assignment, "1 2\n", "3\n", is_hidden=False)
        self.hidden_tc = create_test_case(self.assignment, "99 1\n", "100\n", is_hidden=True)

        self.list_url = reverse('assignment-testcases', kwargs={'assignment_id': self.assignment.id})

    def test_teacher_can_create_test_case(self):
        """Teacher can create both public and hidden test cases."""
        self.client.force_authenticate(user=self.teacher)
        payload = {
            'input_data': '10 20\n',
            'expected_output': '30\n',
            'is_hidden': True,
            'time_limit': 1.5,
            'memory_limit': '256m'
        }
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_hidden'])
        self.assertEqual(response.data['time_limit'], 1.5)

    def test_teacher_sees_all_test_cases(self):
        """Teacher receives both public and hidden test cases with full data."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # Check hidden test case contains real input/output for teacher
        hidden_res = next(tc for tc in response.data if tc['id'] == self.hidden_tc.id)
        self.assertEqual(hidden_res['expected_output'], '100\n')

    def test_student_sees_only_public_test_cases(self):
        """
        CRITICAL SECURITY:
        Student calling GET assignment test cases receives ONLY is_hidden=False test cases.
        Hidden test cases are completely omitted.
        """
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only public_tc!
        self.assertEqual(response.data[0]['id'], self.public_tc.id)

    def test_student_cannot_access_hidden_test_case_detail(self):
        """
        CRITICAL SECURITY:
        Direct GET on a hidden test case by student returns 404 Not Found.
        """
        url = reverse('testcase-detail', kwargs={'pk': self.hidden_tc.id})
        self.client.force_authenticate(user=self.student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_create_test_case(self):
        """Student cannot create test cases (404 / 403)."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.list_url, {'input_data': '', 'expected_output': '42'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_teacher_cannot_manage_test_cases(self):
        """Teacher cannot add or edit test cases for another teacher's classroom."""
        other_teacher = create_teacher("other_teacher")
        self.client.force_authenticate(user=other_teacher)
        response = self.client.post(self.list_url, {'expected_output': 'hack'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 4. MOCK RUNNER & GRADING ENGINE EVALUATION TESTS
# =============================================================================

class MockRunner:
    """Simulates Docker execution outputs for testing engine outcomes."""
    def __init__(self, behavior_map=None, compile_fails=False):
        self.behavior_map = behavior_map or {}
        self.compile_fails = compile_fails

    def compile(self, code, language):
        if self.compile_fails:
            return False, "syntax error: unexpected token ';' at line 1"
        return True, ""

    def run_test_case(self, test_case, code, language):
        behavior = self.behavior_map.get(test_case.id, 'match')

        if behavior == 'match':
            return ExecutionResult(stdout=test_case.expected_output, exit_code=0, time_taken=0.05)
        elif behavior == 'wrong':
            return ExecutionResult(stdout="Wrong output\n", exit_code=0, time_taken=0.06)
        elif behavior == 'runtime_error':
            return ExecutionResult(stdout="", stderr="ZeroDivisionError: division by zero", exit_code=1, time_taken=0.04)
        elif behavior == 'timeout':
            return ExecutionResult(timed_out=True, time_taken=2.1)
        elif behavior == 'oom':
            return ExecutionResult(out_of_memory=True, exit_code=137, time_taken=0.2)
        return ExecutionResult(stdout=test_case.expected_output, exit_code=0, time_taken=0.05)


class GradingEngineEvaluationTest(TestCase):
    """Tests outcome evaluation across all status types and score computations."""

    def setUp(self):
        self.teacher = create_teacher("eval_teacher")
        self.student = create_student("eval_student")
        self.classroom = create_classroom(self.teacher)
        enroll_student(self.student, self.classroom)
        self.assignment = create_assignment(self.classroom, self.teacher, max_marks=100)

        self.tc1 = create_test_case(self.assignment, "1\n", "10\n", is_hidden=False)
        self.tc2 = create_test_case(self.assignment, "2\n", "20\n", is_hidden=True)

        self.submission = create_submission(self.assignment, self.student)

    def test_all_test_cases_accepted(self):
        """When all test cases match, status is ACCEPTED and full marks awarded."""
        runner = MockRunner({self.tc1.id: 'match', self.tc2.id: 'match'})
        res = grade_submission(self.submission.id, custom_runner=runner)

        self.assertEqual(res.status, GradingResult.Outcome.ACCEPTED)
        self.assertEqual(res.passed_count, 2)
        self.assertEqual(res.total_count, 2)
        self.assertEqual(res.score, Decimal('100.00'))

        # Check Submission updated
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.ACCEPTED)
        self.assertIn("Test Cases Passed: 2/2", self.submission.feedback)

    def test_partial_pass_wrong_answer(self):
        """When 1 of 2 test cases fails output match, status is WRONG_ANSWER with proportional score."""
        runner = MockRunner({self.tc1.id: 'match', self.tc2.id: 'wrong'})
        res = grade_submission(self.submission.id, custom_runner=runner)

        self.assertEqual(res.status, GradingResult.Outcome.WRONG_ANSWER)
        self.assertEqual(res.passed_count, 1)
        self.assertEqual(res.total_count, 2)
        self.assertEqual(res.score, Decimal('50.00'))  # 1/2 of 100 marks

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.WRONG_ANSWER)

    def test_compile_error(self):
        """When compilation fails, outcome is COMPILE_ERROR and score is 0."""
        runner = MockRunner(compile_fails=True)
        res = grade_submission(self.submission.id, custom_runner=runner)

        self.assertEqual(res.status, GradingResult.Outcome.COMPILE_ERROR)
        self.assertEqual(res.score, Decimal('0.00'))
        self.assertIn("syntax error", res.error_message)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.COMPILE_ERROR)

    def test_runtime_error(self):
        """When program crashes, outcome is RUNTIME_ERROR."""
        runner = MockRunner({self.tc1.id: 'runtime_error', self.tc2.id: 'match'})
        res = grade_submission(self.submission.id, custom_runner=runner)

        self.assertEqual(res.status, GradingResult.Outcome.RUNTIME_ERROR)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.RUNTIME_ERROR)

    def test_time_limit_exceeded(self):
        """When execution times out, outcome is TIME_LIMIT_EXCEEDED."""
        runner = MockRunner({self.tc1.id: 'timeout', self.tc2.id: 'match'})
        res = grade_submission(self.submission.id, custom_runner=runner)

        self.assertEqual(res.status, GradingResult.Outcome.TIME_LIMIT_EXCEEDED)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.TIME_LIMIT_EXCEEDED)

    def test_memory_limit_exceeded(self):
        """When process exceeds memory limit (OOM), outcome is MEMORY_LIMIT_EXCEEDED."""
        runner = MockRunner({self.tc1.id: 'oom', self.tc2.id: 'match'})
        res = grade_submission(self.submission.id, custom_runner=runner)

        self.assertEqual(res.status, GradingResult.Outcome.MEMORY_LIMIT_EXCEEDED)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.MEMORY_LIMIT_EXCEEDED)

    def test_empty_test_cases_handled_gracefully(self):
        """If assignment has zero test cases, grader records status without crashing."""
        assignment_empty = create_assignment(self.classroom, self.teacher, title="No Tests")
        sub_empty = create_submission(assignment_empty, self.student)

        res = grade_submission(sub_empty.id)
        self.assertEqual(res.status, GradingResult.Outcome.ACCEPTED)
        self.assertEqual(res.total_count, 0)


# =============================================================================
# 5. DOCKER SAFE FALLBACK TEST
# =============================================================================

class DockerSafeFallbackTest(TestCase):
    """
    Verifies that when Docker is unreachable, the engine:
      1. FAILS SAFELY
      2. Does NOT execute student code on host
      3. Sets appropriate warning status and feedback
    """

    def setUp(self):
        self.teacher = create_teacher("safe_teacher")
        self.student = create_student("safe_student")
        self.classroom = create_classroom(self.teacher)
        enroll_student(self.student, self.classroom)
        self.assignment = create_assignment(self.classroom, self.teacher)
        create_test_case(self.assignment, "1", "1")
        self.submission = create_submission(self.assignment, self.student)

    def test_fallback_when_docker_unavailable(self):
        """If Docker daemon is unavailable, engine marks system error without host execution."""
        # Running grade_submission with no custom_runner on a machine without Docker CLI:
        res = grade_submission(self.submission.id)

        # If Docker is not available on this machine (as expected in sandboxed test env):
        docker_ok, _ = is_docker_available()
        if not docker_ok:
            self.assertEqual(res.status, GradingResult.Outcome.SYSTEM_ERROR)
            self.submission.refresh_from_db()
            self.assertIn("Automated evaluation unavailable", self.submission.feedback)


# =============================================================================
# 6. GRADING RESULT API & PRIVACY TESTS
# =============================================================================

class GradingResultAPITest(APITestCase):
    """Tests GET /api/grader/submission/<id>/result/ and POST trigger endpoint."""

    def setUp(self):
        self.teacher = create_teacher("res_teacher")
        self.student = create_student("res_student")
        self.other_student = create_student("res_spy")
        self.classroom = create_classroom(self.teacher)
        enroll_student(self.student, self.classroom)
        enroll_student(self.other_student, self.classroom)
        self.assignment = create_assignment(self.classroom, self.teacher)

        self.tc_pub = create_test_case(self.assignment, "5\n", "25\n", is_hidden=False)
        self.tc_hid = create_test_case(self.assignment, "10\n", "100\n", is_hidden=True)

        self.submission = create_submission(self.assignment, self.student)

        # Pre-generate a grading result with 1 public passed, 1 hidden failed
        runner = MockRunner({self.tc_pub.id: 'match', self.tc_hid.id: 'wrong'})
        self.result = grade_submission(self.submission.id, custom_runner=runner)

        self.url = reverse('grading-result', kwargs={'submission_id': self.submission.id})

    def test_student_sees_sanitized_hidden_test_logs(self):
        """
        CRITICAL PRIVACY TEST:
        Student viewing grading result gets sanitized logs:
        - Public test case shows actual and expected output.
        - Hidden test case has actual_output, expected_output, and diff redacted as '[Hidden]'.
        """
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        logs = response.data['execution_log']
        pub_log = next(log for log in logs if log['test_case_id'] == self.tc_pub.id)
        hid_log = next(log for log in logs if log['test_case_id'] == self.tc_hid.id)

        # Public test case retains expected output
        self.assertEqual(pub_log['expected_output'], '25\n')

        # Hidden test case MUST be masked
        self.assertEqual(hid_log['actual_output'], '[Hidden]')
        self.assertEqual(hid_log['expected_output'], '[Hidden]')
        self.assertEqual(hid_log['diff'], '')

    def test_teacher_sees_full_hidden_test_logs(self):
        """Teacher sees full execution logs including hidden test case output."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        logs = response.data['execution_log']
        hid_log = next(log for log in logs if log['test_case_id'] == self.tc_hid.id)
        # Teacher sees the actual unredacted expected output
        self.assertEqual(hid_log['expected_output'], '100\n')

    def test_other_student_cannot_view_result(self):
        """Another student attempting to view results gets 404."""
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_trigger_grading_endpoint(self):
        """Owner student can trigger evaluation."""
        trigger_url = reverse('trigger-grading', kwargs={'submission_id': self.submission.id})
        self.client.force_authenticate(user=self.student)
        response = self.client.post(trigger_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('result', response.data)


# =============================================================================
# 7. ASYNC TASK QUEUE TEST
# =============================================================================

class AsyncGradingQueueTest(TestCase):
    """Tests non-blocking background queue enqueueing."""

    def test_enqueue_grading_executes_without_error(self):
        teacher = create_teacher("queue_teacher")
        student = create_student("queue_student")
        classroom = create_classroom(teacher)
        enroll_student(student, classroom)
        assignment = create_assignment(classroom, teacher)
        submission = create_submission(assignment, student)

        # Enqueue should return immediately without blocking or raising exceptions
        enqueue_grading(submission.id)
