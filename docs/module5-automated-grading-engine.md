# Module 5 — Automated Grading Engine (Docker Code Execution)

> **LabCraft Backend | Django REST Framework + Docker Sandbox Engine**
> Branch: `feature/automated-grading-engine`
> App: `grader/`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Features Implemented](#2-features-implemented)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Database Models](#4-database-models)
5. [Docker Sandbox Security & Safety Constraints](#5-docker-sandbox-security--safety-constraints)
6. [Output Comparison & Normalization Algorithm](#6-output-comparison--normalization-algorithm)
7. [Asynchronous Background Queue Processing](#7-asynchronous-background-queue-processing)
8. [File-by-File Explanation](#8-file-by-file-explanation)
9. [API Endpoints](#9-api-endpoints)
10. [Example Requests & Responses](#10-example-requests--responses)
11. [Hidden Test Case Privacy & Security](#11-hidden-test-case-privacy--security)
12. [Migration Explanation](#12-migration-explanation)
13. [Test Results](#13-test-results)
14. [How to Push & Create a Pull Request](#14-how-to-push--create-a-pull-request)

---

## 1. Overview

Module 5 implements the **Automated Grading Engine** for LabCraft. When a student submits code (Python, C, C++, Java, JavaScript), the grading engine evaluates the program against test cases (input/expected output pairs) configured by the teacher.

To safeguard the server from malicious or buggy code (such as infinite loops, fork bombs, network attacks, or filesystem deletion), execution happens inside **ephemeral, heavily locked-down Docker containers** with strict CPU, RAM, process, time, and network restrictions.

> **CRITICAL SECURITY GUARANTEE:**
> Student code is **NEVER executed directly on the host operating system or Django web server process**. If the Docker daemon is unreachable or not installed, the engine fails safely and alerts the user rather than risking host compromise.

---

## 2. Features Implemented

| # | Feature | Target Role | Description |
|---|---------|-------------|-------------|
| 1 | **Isolated Docker Sandbox** | System | Ephemeral throwaway containers for Python, C, C++, Java, and JavaScript. |
| 2 | **Strict Container Constraints** | System | `--network none`, `--memory=128m`, `--cpus=1.0`, `--pids-limit=64`, `--user 1000:1000`. |
| 3 | **Timeout (TLE) Handling** | System | Enforces configurable per-test-case time limits (default 2.0s). Exceeding time flags `TIME_LIMIT_EXCEEDED`. |
| 4 | **Memory (MLE) Handling** | System | Memory quota triggers SIGKILL / OOM exit code 137, correctly classified as `MEMORY_LIMIT_EXCEEDED`. |
| 5 | **Output Normalization & Diff** | System | Strips carriage returns (`\r\n` to `\n`), trailing line spaces, and blank lines to evaluate logic rather than whitespace. |
| 6 | **Automated Outcomes** | System | Generates `ACCEPTED` (AC), `WRONG_ANSWER` (WA), `COMPILE_ERROR` (CE), `RUNTIME_ERROR` (RE), `TIME_LIMIT_EXCEEDED` (TLE), `MEMORY_LIMIT_EXCEEDED` (MLE). |
| 7 | **Score Computation** | System | Proportional marks: `score = (passed_tests / total_tests) * assignment.max_marks`. |
| 8 | **Submission & Feedback Update** | System | Automatically updates `Submission.status` and `Submission.feedback` with test breakdown and marks. |
| 9 | **Asynchronous Background Queue** | System | Non-blocking execution via thread pool worker / Celery, returning immediate responses while grading completes in the background. |
| 10 | **Teacher Test Case Management** | Approved Teacher | Create, update, view, and delete public and hidden test cases for assignments in their classrooms. |
| 11 | **Hidden Test Case Privacy** | Student | Students never see hidden test case inputs, expected outputs, or diffs in API responses or logs. |
| 12 | **Safe Docker Fallback** | System | Detects Docker daemon status and safely records `SYSTEM_ERROR` without host execution if Docker is down. |

---

## 3. Architecture Diagram

```
[ Student / Teacher Request ]
             │
             │ HTTP POST /api/submissions/assignment/<id>/submit/
             ▼
[ Submissions App ] ─── Enqueues Background Task ───► [ Grader Async Worker Queue ]
             │                                                         │
             │ Returns HTTP 201 immediately                            ▼
             ▼                                              [ Grader Orchestrator ]
  (Status: "pending")                                       (grader/engine.py)
                                                                       │
                                              ┌────────────────────────┴────────────────────────┐
                                              ▼                                                 ▼
                                   [ Test Cases Query ]                              [ Docker Sandbox Check ]
                                   (Public & Hidden)                                (Fail safely if offline)
                                              │                                                 │
                                              └────────────────────────┬────────────────────────┘
                                                                       │
                                                                       ▼
                                                          [ Ephemeral Docker Sandbox ]
                                                          - Container: python:slim / gcc / openjdk
                                                          - Security: --network none
                                                          - Limits: 128MB RAM, 1.0 CPU, 64 PIDs
                                                          - Timeout: 2.0s per test case
                                                          - User: 1000:1000 (Non-root)
                                                                       │
                                                                       ▼
                                                          [ Output Normalizer & Diff ]
                                                          (grader/comparator.py)
                                                                       │
                                              ┌────────────────────────┴────────────────────────┐
                                              ▼                                                 ▼
                                     [ Pass / Fail Count ]                             [ Score Computation ]
                                     (AC, WA, TLE, MLE, RE, CE)                       (Proportional Marks)
                                              │                                                 │
                                              └────────────────────────┬────────────────────────┘
                                                                       │
                                                                       ▼
                                                          [ Database Persistence ]
                                                          - Submission.status = status
                                                          - Submission.feedback = summary
                                                          - GradingResult.execution_log = JSON
```

---

## 4. Database Models

### `TestCase` Model (`grader/models.py`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField (PK) | Auto-incrementing primary key |
| `assignment` | ForeignKey → Assignment | Assignment this test case belongs to (CASCADE) |
| `input_data` | TextField | Standard input (stdin) fed to the student's program |
| `expected_output` | TextField | Expected standard output (stdout) |
| `is_hidden` | BooleanField (default: False) | If True, inputs and outputs are never revealed to students |
| `time_limit` | FloatField (default: 2.0) | Execution time limit in seconds |
| `memory_limit` | CharField (default: '128m') | Docker RAM quota string (e.g. '128m', '256m') |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last modification timestamp |

### `GradingResult` Model (`grader/models.py`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField (PK) | Auto-incrementing primary key |
| `submission` | OneToOneField → Submission | Submission evaluated |
| `status` | CharField (choices) | `accepted`, `wrong_answer`, `compile_error`, `runtime_error`, `time_limit_exceeded`, `memory_limit_exceeded`, `system_error` |
| `total_count` | PositiveIntegerField | Total number of test cases evaluated |
| `passed_count` | PositiveIntegerField | Number of test cases successfully passed |
| `score` | DecimalField(6, 2) | Marks awarded based on passed test cases |
| `execution_log` | JSONField | Detailed per-test-case logs (timings, diffs, errors) |
| `error_message` | TextField | Compiler or sandbox setup error message |
| `created_at` | DateTimeField | Creation timestamp |

---

## 5. Docker Sandbox Security & Safety Constraints

To guarantee server security, every container runs with the following hardened arguments:

```bash
docker run --rm -i \
  --network none \
  --memory 128m \
  --memory-swap 128m \
  --cpus 1.0 \
  --pids-limit 64 \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  -v /tmp/scratch:/sandbox:ro \
  -w /sandbox \
  python:3.11-slim python3 -u /sandbox/solution.py
```

### Explanations of Security Flags:

1. **`--network none`**: Disables all networking. Containers cannot contact the internet, local network, metadata services (AWS/GCP), or the database. Prevents credential exfiltration and DDoS attacks.
2. **`--memory 128m` & `--memory-swap 128m`**: Restricts RAM usage to 128MB and turns off swap. If code attempts to allocate infinite memory, the Linux kernel terminates the process with SIGKILL (OOM), classified as `MEMORY_LIMIT_EXCEEDED`.
3. **`--cpus 1.0`**: Prevents multi-threaded attacks from monopolizing all server CPU cores.
4. **`--pids-limit 64`**: Limits concurrent processes to 64. Neutralizes fork bombs like `:(){ :|:& };:`.
5. **`--cap-drop ALL`**: Strips all 38+ Linux root capabilities.
6. **`--security-opt no-new-privileges`**: Prevents setuid binaries from gaining additional permissions.
7. **`-v /tmp/scratch:/sandbox:ro`**: The directory containing code is mounted **Read-Only (`:ro`)** during execution so student code cannot modify the binary or other files.
8. **`--rm`**: Ephemeral lifecycle — container is wiped from disk immediately upon termination.

---

## 6. Output Comparison & Normalization Algorithm

Student programs are evaluated based on computational correctness rather than arbitrary whitespace formatting:

```python
def normalize_output(text: str) -> str:
    # 1. Standardize line endings (\r\n -> \n)
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    # 2. Strip trailing whitespace from each line
    lines = [line.rstrip() for line in normalized.split('\n')]
    # 3. Strip trailing blank lines
    while lines and lines[-1] == '':
        lines.pop()
    # 4. Strip leading blank lines
    while lines and lines[0] == '':
        lines.pop(0)
    return '\n'.join(lines)
```

If outputs differ, `difflib.unified_diff` produces a clean diff showing expected vs actual output lines.

---

## 7. Asynchronous Background Queue Processing

Grading multiple test cases in Docker can take several seconds. To prevent HTTP connection timeouts:
1. `POST /api/submissions/assignment/<id>/submit/` saves the submission with `status='pending'`.
2. Calls `enqueue_grading(submission.id)`.
3. Background worker (`ThreadPoolExecutor` / Celery) dequeues the job and executes the sandbox pipeline.
4. The client polls `GET /api/submissions/<id>/` or `GET /api/grader/submission/<id>/result/` to view updated status, marks, and feedback.

---

## 8. File-by-File Explanation

### `backend/grader/models.py`
- Defines `TestCase` with `assignment`, `input_data`, `expected_output`, `is_hidden`, `time_limit`, `memory_limit`.
- Defines `GradingResult` with `submission`, `status`, `passed_count`, `total_count`, `score`, `execution_log`.

### `backend/grader/comparator.py`
- Implements `normalize_output()` and `compare_outputs()` using Python's `difflib`.

### `backend/grader/docker_engine.py`
- Defines `LANGUAGE_CONFIGS` for Python, C, C++, Java, JavaScript.
- Implements `is_docker_available()` with `docker info` probe.
- Implements `DockerSandbox` with `compile()` and `run_test_case()` with full security flags.

### `backend/grader/engine.py`
- Orchestrates compilation, test case iterations, diff generation, score calculation, and model updates.
- Enforces safe fallback if Docker daemon is offline.

### `backend/grader/tasks.py`
- Implements `enqueue_grading()` background task dispatcher.

### `backend/grader/serializers.py`
- `TestCaseTeacherSerializer`: Full access for teachers.
- `TestCaseStudentSerializer`: Redacts `input_data` and `expected_output` for hidden test cases.
- `GradingResultTeacherSerializer`: Full execution logs.
- `GradingResultStudentSerializer`: Redacts hidden test case outputs and diffs.

### `backend/grader/views.py`
- `AssignmentTestCaseListCreateView`: Teacher lists/creates test cases; student lists public test cases.
- `TestCaseDetailView`: Teacher updates/deletes test cases; student views public test case.
- `TriggerGradingView`: Manual/re-grade trigger endpoint.
- `GradingResultView`: Retrieves score and sanitized logs.

---

## 9. API Endpoints

### Test Case Endpoints

| Method | URL | Access | Purpose |
|--------|-----|--------|---------|
| `GET` | `/api/grader/assignment/<id>/test-cases/` | Student / Teacher | Teacher sees all test cases; student sees only public cases |
| `POST` | `/api/grader/assignment/<id>/test-cases/` | Approved Teacher | Create a new test case |
| `GET` | `/api/grader/test-cases/<id>/` | Student / Teacher | View test case (404 for student if hidden) |
| `PATCH` | `/api/grader/test-cases/<id>/` | Approved Teacher | Update test case |
| `DELETE` | `/api/grader/test-cases/<id>/` | Approved Teacher | Delete test case |

### Evaluation Endpoints

| Method | URL | Access | Purpose |
|--------|-----|--------|---------|
| `POST` | `/api/grader/submission/<id>/grade/` | Student Owner / Teacher | Trigger/re-run automated evaluation |
| `GET` | `/api/grader/submission/<id>/result/` | Student Owner / Teacher | Retrieve evaluation logs and score |

---

## 10. Example Requests & Responses

### 1. Teacher Creates Hidden Test Case

**Request:**
```http
POST /api/grader/assignment/1/test-cases/
Authorization: Bearer <teacher_token>
Content-Type: application/json

{
  "input_data": "100 200\n",
  "expected_output": "300\n",
  "is_hidden": true,
  "time_limit": 2.0,
  "memory_limit": "128m"
}
```

**Response (201 Created):**
```json
{
  "id": 12,
  "assignment_id": 1,
  "input_data": "100 200\n",
  "expected_output": "300\n",
  "is_hidden": true,
  "time_limit": 2.0,
  "memory_limit": "128m",
  "created_at": "2026-11-10T12:00:00Z",
  "updated_at": "2026-11-10T12:00:00Z"
}
```

---

### 2. Student Views Assignment Test Cases (Hidden Case Redacted)

**Request:**
```http
GET /api/grader/assignment/1/test-cases/
Authorization: Bearer <student_token>
```

**Response (200 OK):**
```json
[
  {
    "id": 11,
    "assignment_id": 1,
    "input_data": "2 3\n",
    "expected_output": "5\n",
    "is_hidden": false,
    "time_limit": 2.0,
    "memory_limit": "128m"
  }
]
```
*(Notice: Hidden Test Case #12 is completely excluded from the list!)*

---

### 3. Student Views Grading Result (Sanitized Logs)

**Request:**
```http
GET /api/grader/submission/42/result/
Authorization: Bearer <student_token>
```

**Response (200 OK):**
```json
{
  "id": 8,
  "submission_id": 42,
  "status": "wrong_answer",
  "total_count": 2,
  "passed_count": 1,
  "score": "50.00",
  "pass_percentage": 50.0,
  "execution_log": [
    {
      "test_case_id": 11,
      "is_hidden": false,
      "status": "accepted",
      "time_taken": 0.045,
      "actual_output": "5\n",
      "expected_output": "5\n",
      "diff": "",
      "error_message": ""
    },
    {
      "test_case_id": 12,
      "is_hidden": true,
      "status": "wrong_answer",
      "time_taken": 0.052,
      "actual_output": "[Hidden]",
      "expected_output": "[Hidden]",
      "diff": "",
      "error_message": "Output did not match expected."
    }
  ],
  "error_message": "",
  "created_at": "2026-11-10T12:01:00Z"
}
```

---

## 11. Hidden Test Case Privacy & Security

| Security Rule | Mechanism | Location |
|---|---|---|
| Students cannot list hidden test cases | `test_cases.filter(is_hidden=False)` | `AssignmentTestCaseListCreateView` |
| Students cannot GET single hidden test case | Returns `404 Not Found` if `is_hidden=True` | `TestCaseDetailView` |
| Students cannot see hidden input/output in results | Masked as `"[Hidden]"` and `diff=""` | `GradingResultStudentSerializer` |
| Students cannot create or modify test cases | Requires `is_teacher` ownership | `AssignmentTestCaseListCreateView` |
| Teachers cannot access other teachers' test cases | Filtered by `classroom__teacher=request.user` | `TestCaseDetailView` |

---

## 12. Migration Explanation

```bash
# 1. Create migration file
python manage.py makemigrations grader

# 2. Apply migration to database
python manage.py migrate grader
```

**What this did:**
- Created `grader/migrations/0001_initial.py` defining tables `grader_testcase` and `grader_gradingresult`.
- Applied foreign key dependencies to `assignments_assignment` and `submissions_submission`.

---

## 13. Test Results

### Test Suite Execution Command:
```bash
python manage.py test grader -v 2
```
```
Ran 25 tests in 25.724s
OK
```

### Grader Module Breakdown:
- `ComparatorTest` (4 tests): CRLF handling, line trimming, diff calculation.
- `TestCaseModelTest` (2 tests): Model defaults and string representations.
- `TestCaseAPITest` (6 tests): Teacher CRUD, student public view, hidden test protection.
- `GradingEngineEvaluationTest` (7 tests): AC, WA, CE, RE, TLE, MLE, empty cases, score computation.
- `DockerSafeFallbackTest` (1 test): Fallback to `SYSTEM_ERROR` without host code execution.
- `GradingResultAPITest` (4 tests): Student sanitization, teacher full access, permission checks.
- `AsyncGradingQueueTest` (1 test): Background thread pool worker dispatch.

### Complete Platform Test Suite (Modules 1–5):
```bash
python manage.py test accounts classrooms assignments submissions grader -v 2
```
```
Ran 192 tests in 282.115s
OK
```
**All 192 tests passed with 100% success rate.**

---

## 14. How to Push & Create a Pull Request

All completed work is committed on `feature/automated-grading-engine`.

### Step 1: Push to GitHub
```powershell
cd d:\PROGRAMMING\PROJECTS\LabCraft\LabCraft
git push -u origin feature/automated-grading-engine
```

### Step 2: Create Pull Request Targeting `develop`
1. Navigate to: `https://github.com/sakshivavale/LabCraft`
2. Click **"Compare & pull request"**.
3. Set:
   - **Base branch:** `develop`
   - **Compare branch:** `feature/automated-grading-engine`
4. Title:
   ```text
   feat(grader): implement Module 5 — Automated Grading Engine (Docker Code Execution)
   ```
5. Description:
   ```markdown
   ## Module 5: Automated Grading Engine (Docker Code Execution)

   ### Features Implemented
   - Isolated Docker container sandbox engine with strict security parameters (`--network none`, `--memory 128m`, `--cpus 1.0`, `--pids-limit 64`, `--user 1000:1000`, `--rm`).
   - Multi-language support (Python, C, C++, Java, JavaScript).
   - Test case management API for teachers (public & hidden test cases).
   - Strict student privacy: hidden test case inputs, outputs, and diffs are never exposed.
   - Output normalization and unified diff generation.
   - Comprehensive outcome evaluation: ACCEPTED, WRONG_ANSWER, COMPILE_ERROR, RUNTIME_ERROR, TIME_LIMIT_EXCEEDED, MEMORY_LIMIT_EXCEEDED.
   - Proportional scoring based on passed test cases and assignment max marks.
   - Asynchronous background task queue processing.
   - Safe Docker fallback: student code is never executed directly on host if Docker is unavailable.

   ### Test Results
   - `grader` tests: 25 passed (100%)
   - Full test suite (Modules 1–5): 192 passed (100%)
   ```
6. Click **"Create pull request"**.
7. **Do not merge yet.** Wait for review and approval.

