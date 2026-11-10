"""
grader/comparator.py

Output Comparison & Normalization Engine for LabCraft.

Why do we need output normalization?
  In programming assignments, student programs often output correct values
  but may have slight formatting differences such as:
    1. Trailing spaces at the end of lines ("hello \n" vs "hello\n")
    2. Carriage return vs newline differences ("\r\n" on Windows vs "\n" on Linux)
    3. Extra blank lines at the end of the output

  The competitive programming standard (used by Codeforces, LeetCode, HackerRank)
  strips trailing whitespace per line and trailing empty lines from both outputs
  before comparison. This ensures students are evaluated on their algorithm's
  logic, not invisible whitespace differences.
"""

import difflib


def normalize_output(text: str) -> str:
    """
    Normalizes a text string for whitespace-insensitive comparison.

    Steps:
      1. Replace Windows CRLF (\r\n) with Unix LF (\n).
      2. Strip trailing whitespace from each line.
      3. Strip leading and trailing empty lines.
      4. Ensure a single consistent newline between lines.

    Example:
      Input:  "42   \r\n84  \r\n\r\n"
      Output: "42\n84"
    """
    if text is None:
        return ""

    # 1. Unify newline characters
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')

    # 2. Split into lines and strip trailing whitespace from each line
    lines = [line.rstrip() for line in normalized.split('\n')]

    # 3. Strip trailing blank lines
    while lines and lines[-1] == '':
        lines.pop()

    # 4. Strip leading blank lines
    while lines and lines[0] == '':
        lines.pop(0)

    # 5. Join lines back together with clean \n
    return '\n'.join(lines)


def compare_outputs(actual_output: str, expected_output: str) -> tuple[bool, str]:
    """
    Compares the student's actual program output against the expected test case output.

    Returns:
      (is_match: bool, diff_summary: str)
      - is_match: True if outputs match after normalization, False otherwise.
      - diff_summary: Empty string on match, or a readable line diff explaining differences.
    """
    norm_actual = normalize_output(actual_output)
    norm_expected = normalize_output(expected_output)

    if norm_actual == norm_expected:
        return True, ""

    # If outputs differ, generate a unified diff for feedback
    actual_lines = norm_actual.splitlines(keepends=True)
    expected_lines = norm_expected.splitlines(keepends=True)

    # difflib.unified_diff generates standard +/- line differences
    diff = list(
        difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile='expected_output',
            tofile='student_output',
            lineterm=''
        )
    )

    diff_text = '\n'.join(diff[:20])  # Limit diff to first 20 lines to keep logs compact
    if len(diff) > 20:
        diff_text += "\n... (remaining diff truncated)"

    return False, diff_text

