"""
grader/engine.py

Core Grading Engine Orchestrator for LabCraft.

This module ties together:
  - Database objects (Submission, Assignment, TestCase, GradingResult)
  - Docker sandbox execution (docker_engine.py)
  - Output comparison and normalization (comparator.py)
  - Status lifecycle updates and score computation

Execution Pipeline:
  1. Fetch the Submission and its Assignment's TestCases.
  2. Verify Docker sandbox availability. Fail safely if unavailable.
  3. Write code to an isolated temporary scratchpad directory.
  4. Compile source code (for C, C++, Java). Catch Compile Errors.
  5. Run each TestCase inside an ephemeral Docker container.
  6. Normalize and compare outputs. Record timings and diffs.
  7. Compute score = (passed_tests / total_tests) * assignment.max_marks.
  8. Update Submission.status, Submission.feedback, and create GradingResult.
  9. Clean up temporary directories.
"""

import os
import tempfile
import shutil
from typing import Optional, List, Dict, Any
from decimal import Decimal

from django.utils import timezone
from submissions.models import Submission
from assignments.models import Assignment
from .models import TestCase, GradingResult
from .comparator import compare_outputs, normalize_output
from .docker_engine import DockerSandbox, is_docker_available, ExecutionResult, LANGUAGE_CONFIGS


def grade_submission(submission_id: int, custom_runner=None) -> GradingResult:
    """
    Evaluates a student's submission against all configured test cases.

    Parameters:
      submission_id: Primary key of the Submission to grade.
      custom_runner: Optional test hook / runner override for unit tests.

    Returns:
      GradingResult: The saved database record with execution breakdown and score.
    """
    # 1. Fetch the submission from database
    submission = Submission.objects.select_related('assignment').get(id=submission_id)
    assignment = submission.assignment

    # Update status to 'running' while evaluation is underway
    submission.status = Submission.Status.RUNNING
    submission.feedback = "Grader is currently evaluating test cases inside sandbox..."
    submission.save(update_fields=['status', 'feedback'])

    # 2. Fetch all test cases for this assignment
    test_cases = list(assignment.test_cases.all().order_by('id'))
    total_cases = len(test_cases)

    # Handle edge case: Assignment has no test cases configured yet
    if total_cases == 0:
        result, _ = GradingResult.objects.update_or_create(
            submission=submission,
            defaults={
                'status': GradingResult.Outcome.ACCEPTED,
                'total_count': 0,
                'passed_count': 0,
                'score': Decimal('0.00'),
                'execution_log': [],
                'error_message': 'No test cases configured for this assignment.',
            }
        )
        submission.status = Submission.Status.ACCEPTED
        submission.feedback = "Submission recorded. No automated test cases configured for this assignment."
        submission.save(update_fields=['status', 'feedback'])
        return result

    # 3. Check Docker sandbox availability (Fail Safely rule)
    docker_ok, docker_msg = is_docker_available()

    # If no custom test runner is supplied and Docker is unavailable -> fail safely!
    if not docker_ok and custom_runner is None:
        result, _ = GradingResult.objects.update_or_create(
            submission=submission,
            defaults={
                'status': GradingResult.Outcome.SYSTEM_ERROR,
                'total_count': total_cases,
                'passed_count': 0,
                'score': Decimal('0.00'),
                'execution_log': [],
                'error_message': docker_msg,
            }
        )
        submission.status = Submission.Status.RUNTIME_ERROR
        submission.feedback = (
            f"Automated evaluation unavailable: {docker_msg} "
            "Please notify your instructor."
        )
        submission.save(update_fields=['status', 'feedback'])
        return result

    # 4. Set up temporary directory for compiling and running
    temp_dir = tempfile.mkdtemp(prefix=f"labcraft_sub_{submission.id}_")
    sandbox = DockerSandbox(submission.source_code, submission.language)

    try:
        # Write student code to source file
        lang_config = LANGUAGE_CONFIGS.get(submission.language.lower(), LANGUAGE_CONFIGS['other'])
        file_path = os.path.join(temp_dir, lang_config['file_name'])

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(submission.source_code)

        # 5. Compilation phase (if compiled language)
        if custom_runner is None:
            compile_ok, compile_err = sandbox.compile(temp_dir)
        else:
            # Test hook
            compile_ok, compile_err = custom_runner.compile(submission.source_code, submission.language)

        if not compile_ok:
            # Compilation failed! Stop immediately with COMPILE_ERROR
            result, _ = GradingResult.objects.update_or_create(
                submission=submission,
                defaults={
                    'status': GradingResult.Outcome.COMPILE_ERROR,
                    'total_count': total_cases,
                    'passed_count': 0,
                    'score': Decimal('0.00'),
                    'execution_log': [],
                    'error_message': compile_err,
                }
            )
            submission.status = Submission.Status.COMPILE_ERROR
            submission.feedback = f"Compile Error:\n{compile_err}"
            submission.save(update_fields=['status', 'feedback'])
            return result

        # 6. Evaluation phase: Run against each TestCase
        passed_count = 0
        overall_status = GradingResult.Outcome.ACCEPTED
        execution_logs: List[Dict[str, Any]] = []

        for tc in test_cases:
            if custom_runner is None:
                exec_res = sandbox.run_test_case(
                    temp_dir=temp_dir,
                    input_data=tc.input_data,
                    time_limit=tc.time_limit,
                    memory_limit=tc.memory_limit
                )
            else:
                exec_res = custom_runner.run_test_case(tc, submission.source_code, submission.language)

            # Analyze execution outcome
            tc_status = GradingResult.Outcome.ACCEPTED
            tc_error = ""

            if exec_res.timed_out:
                tc_status = GradingResult.Outcome.TIME_LIMIT_EXCEEDED
                tc_error = f"Time Limit Exceeded (>{tc.time_limit}s)"
            elif exec_res.out_of_memory:
                tc_status = GradingResult.Outcome.MEMORY_LIMIT_EXCEEDED
                tc_error = f"Memory Limit Exceeded (>{tc.memory_limit})"
            elif exec_res.exit_code != 0:
                tc_status = GradingResult.Outcome.RUNTIME_ERROR
                tc_error = exec_res.stderr.strip() or f"Runtime Error (Exit Code {exec_res.exit_code})"
            else:
                # Execution exited normally (exit code 0). Now check output!
                matches, diff_info = compare_outputs(exec_res.stdout, tc.expected_output)
                if matches:
                    tc_status = GradingResult.Outcome.ACCEPTED
                else:
                    tc_status = GradingResult.Outcome.WRONG_ANSWER
                    tc_error = "Output did not match expected."

            # Update overall status: the first non-accepted status becomes the overall status
            if tc_status == GradingResult.Outcome.ACCEPTED:
                passed_count += 1
            elif overall_status == GradingResult.Outcome.ACCEPTED:
                overall_status = tc_status

            # Append structured per-test case log
            execution_logs.append({
                'test_case_id': tc.id,
                'is_hidden': tc.is_hidden,
                'status': tc_status,
                'time_taken': exec_res.time_taken,
                'actual_output': exec_res.stdout,
                'expected_output': tc.expected_output,
                'diff': diff_info if tc_status == GradingResult.Outcome.WRONG_ANSWER else "",
                'error_message': tc_error,
            })

        # 7. Compute score
        score_ratio = Decimal(passed_count) / Decimal(total_cases)
        awarded_score = round(score_ratio * Decimal(assignment.max_marks), 2)

        # 8. Build student-friendly feedback summary
        summary_lines = [
            f"Test Cases Passed: {passed_count}/{total_cases}",
            f"Marks Awarded: {awarded_score}/{assignment.max_marks}",
            f"Overall Status: {dict(GradingResult.Outcome.choices).get(overall_status, overall_status)}",
        ]

        # Add brief breakdown of each test case
        for idx, log in enumerate(execution_logs, 1):
            tag = "Hidden" if log['is_hidden'] else "Public"
            symbol = "✅ Passed" if log['status'] == GradingResult.Outcome.ACCEPTED else f"❌ {log['status'].replace('_', ' ').title()}"
            summary_lines.append(f"  • Test #{idx} ({tag}): {symbol} ({log['time_taken']}s)")

        feedback_text = "\n".join(summary_lines)

        # 9. Update database records
        # Map GradingResult outcome to Submission.Status choices
        submission_status_map = {
            GradingResult.Outcome.ACCEPTED: Submission.Status.ACCEPTED,
            GradingResult.Outcome.WRONG_ANSWER: Submission.Status.WRONG_ANSWER,
            GradingResult.Outcome.COMPILE_ERROR: Submission.Status.COMPILE_ERROR,
            GradingResult.Outcome.RUNTIME_ERROR: Submission.Status.RUNTIME_ERROR,
            GradingResult.Outcome.TIME_LIMIT_EXCEEDED: Submission.Status.TIME_LIMIT_EXCEEDED,
            GradingResult.Outcome.MEMORY_LIMIT_EXCEEDED: Submission.Status.MEMORY_LIMIT_EXCEEDED,
            GradingResult.Outcome.SYSTEM_ERROR: Submission.Status.RUNTIME_ERROR,
        }

        submission.status = submission_status_map.get(overall_status, Submission.Status.WRONG_ANSWER)
        submission.feedback = feedback_text
        submission.save(update_fields=['status', 'feedback'])

        result, _ = GradingResult.objects.update_or_create(
            submission=submission,
            defaults={
                'status': overall_status,
                'total_count': total_cases,
                'passed_count': passed_count,
                'score': awarded_score,
                'execution_log': execution_logs,
                'error_message': '',
            }
        )

        return result

    finally:
        # 10. Always clean up temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)
