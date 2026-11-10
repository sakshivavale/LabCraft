# Module 6 — Analytics Dashboard & Final Platform Integration

> **LabCraft Platform | Full-Stack Analytics, Aggregations, & Dashboard System**
> Branch: `feature/analytics-dashboard`
> Target Branch: `develop`
> Backend App: `backend/analytics/`
> Frontend Pages: `frontend/src/pages/StudentDashboardPage.jsx`, `frontend/src/pages/TeacherDashboardPage.jsx`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Features Implemented](#2-features-implemented)
3. [Architecture & Aggregation Strategy](#3-architecture--aggregation-strategy)
4. [Role-Based Access Control (RBAC) Matrix](#4-role-based-access-control-rbac-matrix)
5. [API Specifications](#5-api-specifications)
6. [Example Requests & Full Responses](#6-example-requests--full-responses)
7. [Frontend Architecture & UI Walkthrough](#7-frontend-architecture--ui-walkthrough)
8. [File-by-File Technical Walkthrough](#8-file-by-file-technical-walkthrough)
9. [Test Suite Verification (All 204 Tests Passing)](#9-test-suite-verification-all-204-tests-passing)
10. [How to Push & Create a Pull Request](#10-how-to-push--create-a-pull-request)

---

## 1. Overview

Module 6 completes the core platform by implementing the **Analytics Dashboard & Final Platform Integration** for LabCraft.

This module provides real-time, aggregated learning intelligence for both Students and Instructors:
- **For Students:** A comprehensive cockpit displaying personal completion rates, acceptance rates (% of submissions passing all test cases), marks earned across all enrolled classrooms, verdict breakdown (AC, WA, TLE, RE, CE), and a unified assignment status table with direct links to the Monaco Code Editor and Submission History.
- **For Teachers:** A multi-classroom command center displaying active student enrollment, total submissions, overall acceptance rates, grade averages, classroom-specific student leaderboards, assignment gradebooks, and score distribution histograms.

> **KEY ARCHITECTURAL HIGHLIGHT:**
> The `analytics` module does **NOT** store redundant or cached analytics records in database tables. Instead, all metrics are aggregated dynamically using optimized Django ORM and SQL aggregation functions (`Count`, `Avg`, `Max`, `Min`, `Q` conditional filtering). This ensures 100% real-time accuracy, zero cache-invalidation bugs, and zero database bloat.

---

## 2. Features Implemented

| # | Feature | Target User | Description |
|---|---------|-------------|-------------|
| 1 | **Student Overview Metrics** | Student | Calculates total enrolled classrooms, completed assignments, pending assignments, acceptance rate (%), and total marks earned. |
| 2 | **Student Verdict Breakdown** | Student | Distribution of submission outcomes: `accepted`, `wrong_answer`, `time_limit_exceeded`, `runtime_error`, `compile_error`, `memory_limit_exceeded`. |
| 3 | **Per-Classroom Student Progress** | Student | Progress cards for each enrolled classroom with instructor name, assignment count, and marks earned. |
| 4 | **Unified Assignment Action Table** | Student | Renders all assignments across classrooms with deadline, best submission status badge, best score, attempts, and 1-click links to Code Editor or History. |
| 5 | **Teacher Multi-Classroom Overview** | Approved Teacher | Aggregates all classrooms instructed by the teacher, unique enrolled student count, total assignments, submissions count, acceptance rate, and average score. |
| 6 | **Global Verdict Distribution** | Approved Teacher | System-wide breakdown of grading outcomes across all teacher's classrooms. |
| 7 | **Classroom Performance & Leaderboard** | Approved Teacher | Detailed classroom analytics endpoint providing student leaderboards (ranked by total score and completed labs) and assignment submission rates. |
| 8 | **Assignment Gradebook & Score Buckets** | Approved Teacher | Per-assignment analytics endpoint featuring score distribution histograms (0–20%, 21–40%, 41–60%, 61–80%, 81–100%) and a full roster gradebook. |
| 9 | **Role-Based Security & Isolation** | All | Enforces strict role checks: students cannot access teacher metrics; teachers cannot access metrics for classrooms they do not own; unapproved teachers and unauthenticated requests are blocked. |
| 10 | **Interactive React Dashboards** | All | Dedicated, responsive UI components (`StudentDashboardPage.jsx`, `TeacherDashboardPage.jsx`) built with dark navy theme matching the Monaco Code Editor. |
| 11 | **Smart Role Navigation** | All | Navigation bar (`Navbar.jsx`) dynamically surfaces role-specific dashboard shortcuts and routes users appropriately upon login. |

---

## 3. Architecture & Aggregation Strategy

```
                                  [ Client Browser ]
                                     │         │
                 ┌───────────────────┘         └───────────────────┐
                 ▼                                                 ▼
        [ Student Flow ]                                  [ Teacher Flow ]
        GET /api/analytics/student/dashboard/             GET /api/analytics/teacher/dashboard/
        GET /api/analytics/classroom/<id>/                GET /api/analytics/assignment/<id>/
                 │                                                 │
                 └───────────────────┬─────────────────────────────┘
                                     ▼
                           [ Django REST Framework ]
                           [ Role & Permission Check ]
                           - IsAuthenticated
                           - IsStudentUser / IsApprovedTeacherUser
                           - Classroom Ownership Check (Teacher)
                                     │
                                     ▼
                      [ Optimized Single-Pass ORM ]
             ┌───────────────────────┼───────────────────────┐
             ▼                       ▼                       ▼
      [ classrooms ]          [ assignments ]          [ submissions ]
      - Classroom             - Assignment             - Submission
      - ClassroomMembership   - TestCase               - GradingResult
             │                       │                       │
             └───────────────────────┼───────────────────────┘
                                     ▼
                 [ SQL Aggregation: Count, Avg, Max, Q ]
             - Single query verdict distribution
             - Elimination of N+1 database queries
             - Real-time calculation without caching
```

### Why Dynamic Aggregation?

1. **Zero State Drift:** Pre-computed counters or statistics stored in separate summary tables frequently drift out of sync when submissions are re-evaluated, deleted, or late. Computing directly from base tables ensures single source of truth.
2. **High Performance via SQL Filters:** Using conditional ORM expressions like:
   ```python
   status_counts = submissions.aggregate(
       accepted=Count('id', filter=Q(status='accepted')),
       wrong_answer=Count('id', filter=Q(status='wrong_answer')),
       time_limit_exceeded=Count('id', filter=Q(status='time_limit_exceeded')),
       runtime_error=Count('id', filter=Q(status='runtime_error')),
       compile_error=Count('id', filter=Q(status='compile_error')),
       memory_limit_exceeded=Count('id', filter=Q(status='memory_limit_exceeded')),
   )
   ```
   executes as a single `SELECT COUNT(CASE WHEN status='accepted' THEN 1 END)...` SQL query, which completes in milliseconds even over thousands of rows.

---

## 4. Role-Based Access Control (RBAC) Matrix

| Endpoint | Student | Approved Teacher | Pending/Unapproved Teacher | Anonymous |
|---|---|---|---|---|
| `GET /api/analytics/student/dashboard/` | ✅ **200 OK** (Own data only) | 🚫 **403 Forbidden** | 🚫 **403 Forbidden** | 🚫 **401 Unauthorized** |
| `GET /api/analytics/teacher/dashboard/` | 🚫 **403 Forbidden** | ✅ **200 OK** (Owned classrooms) | 🚫 **403 Forbidden** | 🚫 **401 Unauthorized** |
| `GET /api/analytics/classroom/<id>/` | 🚫 **403 Forbidden** | ✅ **200 OK** (Owned classroom) <br>🚫 **404 Not Found** (Other teacher's classroom) | 🚫 **403 Forbidden** | 🚫 **401 Unauthorized** |
| `GET /api/analytics/assignment/<id>/` | 🚫 **403 Forbidden** | ✅ **200 OK** (Owned assignment) <br>🚫 **404 Not Found** (Other teacher's assignment) | 🚫 **403 Forbidden** | 🚫 **401 Unauthorized** |

---

## 5. API Specifications

### 5.1 Student Dashboard
- **URL:** `GET /api/analytics/student/dashboard/`
- **Auth:** Bearer JWT (Student only)
- **Status Codes:** `200 OK`, `401 Unauthorized`, `403 Forbidden`
- **Output:**
  - `summary`: High-level counters, completion rate, acceptance rate, total marks.
  - `status_distribution`: Counts of AC, WA, TLE, RE, CE, MLE.
  - `classrooms`: List of enrolled classrooms with individual assignment progress.
  - `assignments`: Detailed list of all assignments with submission status, best score, attempts count, and timestamps.

### 5.2 Teacher Multi-Classroom Dashboard
- **URL:** `GET /api/analytics/teacher/dashboard/`
- **Auth:** Bearer JWT (Approved Teacher only)
- **Status Codes:** `200 OK`, `401 Unauthorized`, `403 Forbidden`
- **Output:**
  - `summary`: Total classrooms, enrolled students, assignments, submissions, acceptance rate, average score.
  - `status_distribution`: Aggregated grading outcomes across all instructor's classrooms.
  - `classrooms`: Summary card data for each taught classroom (student count, submission rate %, avg score).
  - `recent_submissions`: Feed of latest 10 submissions with student username, score, verdict, and timestamp.

### 5.3 Classroom Analytics & Leaderboard
- **URL:** `GET /api/analytics/classroom/<id>/`
- **Auth:** Bearer JWT (Instructor of classroom only)
- **Status Codes:** `200 OK`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`
- **Output:**
  - `classroom`: Metadata, enrollment count, submissions count, submission rate, average score.
  - `status_distribution`: Outcome counts within this classroom.
  - `assignments`: Per-assignment statistics (submitted student count, submission rate %, avg score, high/low).
  - `leaderboard`: Ranked list of students in the classroom ordered by `total_score` descending and `assignments_completed` descending.

### 5.4 Assignment Analytics & Gradebook
- **URL:** `GET /api/analytics/assignment/<id>/`
- **Auth:** Bearer JWT (Instructor of assignment's classroom only)
- **Status Codes:** `200 OK`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`
- **Output:**
  - `assignment`: Metadata, enrolled students, submitted students, submission rate %, average score, highest/lowest score.
  - `status_distribution`: Outcome counts for this assignment.
  - `score_distribution`: 5-bucket percentage breakdown (`0_to_20_pct`, `21_to_40_pct`, `41_to_60_pct`, `61_to_80_pct`, `81_to_100_pct`).
  - `gradebook`: Complete roster of enrolled students indicating submission status, attempt count, best score, and latest submission ID for one-click code inspection.

---

## 6. Example Requests & Full Responses

### Example 1: Student Dashboard
**Request:**
```http
GET /api/analytics/student/dashboard/ HTTP/1.1
Host: localhost:8000
Authorization: Bearer <student_jwt_token>
```

**Response (HTTP 200 OK):**
```json
{
  "summary": {
    "total_classrooms": 2,
    "total_assignments": 4,
    "submitted_assignments": 3,
    "pending_assignments": 1,
    "total_submissions": 5,
    "acceptance_rate_percentage": 60.0,
    "total_marks_earned": 280.0,
    "total_marks_possible": 300.0,
    "average_score_percentage": 93.33
  },
  "status_distribution": {
    "accepted": 3,
    "wrong_answer": 1,
    "time_limit_exceeded": 1,
    "runtime_error": 0,
    "compile_error": 0,
    "memory_limit_exceeded": 0,
    "pending": 0,
    "running": 0
  },
  "classrooms": [
    {
      "id": 1,
      "name": "Data Structures & Algorithms",
      "code": "DSA2026",
      "teacher_name": "Prof. Alan Turing",
      "total_assignments": 2,
      "submitted_assignments": 2,
      "earned_marks": 200.0,
      "possible_marks": 200.0
    },
    {
      "id": 2,
      "name": "Object-Oriented Programming",
      "code": "OOP2026",
      "teacher_name": "Prof. Ada Lovelace",
      "total_assignments": 2,
      "submitted_assignments": 1,
      "earned_marks": 80.0,
      "possible_marks": 100.0
    }
  ],
  "assignments": [
    {
      "id": 10,
      "title": "Binary Search Tree Implementation",
      "classroom_name": "Data Structures & Algorithms",
      "due_date": "2026-11-20T23:59:59Z",
      "is_submitted": true,
      "submission_count": 2,
      "best_status": "accepted",
      "best_score": 100.0,
      "max_score": 100.0,
      "latest_submission_at": "2026-11-10T14:22:00Z"
    },
    {
      "id": 11,
      "title": "Graph Shortest Path (Dijkstra)",
      "classroom_name": "Data Structures & Algorithms",
      "due_date": "2026-11-25T23:59:59Z",
      "is_submitted": true,
      "submission_count": 1,
      "best_status": "accepted",
      "best_score": 100.0,
      "max_score": 100.0,
      "latest_submission_at": "2026-11-10T15:10:00Z"
    },
    {
      "id": 20,
      "title": "Inheritance & Polymorphism Lab",
      "classroom_name": "Object-Oriented Programming",
      "due_date": "2026-11-30T23:59:59Z",
      "is_submitted": true,
      "submission_count": 2,
      "best_status": "accepted",
      "best_score": 80.0,
      "max_score": 100.0,
      "latest_submission_at": "2026-11-10T16:00:00Z"
    },
    {
      "id": 21,
      "title": "Design Patterns Challenge",
      "classroom_name": "Object-Oriented Programming",
      "due_date": "2026-12-05T23:59:59Z",
      "is_submitted": false,
      "submission_count": 0,
      "best_status": null,
      "best_score": 0.0,
      "max_score": 100.0,
      "latest_submission_at": null
    }
  ]
}
```

---

### Example 2: Classroom Analytics & Leaderboard
**Request:**
```http
GET /api/analytics/classroom/1/ HTTP/1.1
Host: localhost:8000
Authorization: Bearer <teacher_jwt_token>
```

**Response (HTTP 200 OK):**
```json
{
  "classroom": {
    "id": 1,
    "name": "Data Structures & Algorithms",
    "code": "DSA2026",
    "teacher_name": "Prof. Alan Turing",
    "enrolled_student_count": 25,
    "total_assignments": 2,
    "total_submissions": 48,
    "overall_submission_rate_percentage": 88.0,
    "average_score": 84.5
  },
  "status_distribution": {
    "accepted": 36,
    "wrong_answer": 7,
    "time_limit_exceeded": 3,
    "runtime_error": 2,
    "compile_error": 0,
    "memory_limit_exceeded": 0,
    "pending": 0,
    "running": 0
  },
  "assignments": [
    {
      "id": 10,
      "title": "Binary Search Tree Implementation",
      "max_score": 100.0,
      "due_date": "2026-11-20T23:59:59Z",
      "submission_count": 26,
      "unique_students_submitted": 23,
      "submission_rate_percentage": 92.0,
      "average_score": 88.0,
      "highest_score": 100.0,
      "lowest_score": 40.0
    },
    {
      "id": 11,
      "title": "Graph Shortest Path (Dijkstra)",
      "max_score": 100.0,
      "due_date": "2026-11-25T23:59:59Z",
      "submission_count": 22,
      "unique_students_submitted": 21,
      "submission_rate_percentage": 84.0,
      "average_score": 81.0,
      "highest_score": 100.0,
      "lowest_score": 20.0
    }
  ],
  "leaderboard": [
    {
      "rank": 1,
      "student_id": 102,
      "student_username": "grace_hopper",
      "student_email": "hopper@navy.mil",
      "total_score": 200.0,
      "max_possible_score": 200.0,
      "score_percentage": 100.0,
      "assignments_completed": 2
    },
    {
      "rank": 2,
      "student_id": 105,
      "student_username": "john_von_neumann",
      "student_email": "neumann@ias.edu",
      "total_score": 190.0,
      "max_possible_score": 200.0,
      "score_percentage": 95.0,
      "assignments_completed": 2
    }
  ]
}
```

---

### Example 3: Assignment Analytics & Gradebook
**Request:**
```http
GET /api/analytics/assignment/10/ HTTP/1.1
Host: localhost:8000
Authorization: Bearer <teacher_jwt_token>
```

**Response (HTTP 200 OK):**
```json
{
  "assignment": {
    "id": 10,
    "title": "Binary Search Tree Implementation",
    "classroom_name": "Data Structures & Algorithms",
    "max_score": 100.0,
    "due_date": "2026-11-20T23:59:59Z",
    "total_enrolled_students": 25,
    "submitted_student_count": 23,
    "submission_rate_percentage": 92.0,
    "average_score": 88.0,
    "highest_score": 100.0,
    "lowest_score": 40.0
  },
  "status_distribution": {
    "accepted": 19,
    "wrong_answer": 3,
    "time_limit_exceeded": 1,
    "runtime_error": 0,
    "compile_error": 0,
    "memory_limit_exceeded": 0,
    "pending": 0,
    "running": 0
  },
  "score_distribution": {
    "0_to_20_pct": 0,
    "21_to_40_pct": 1,
    "41_to_60_pct": 2,
    "61_to_80_pct": 4,
    "81_to_100_pct": 16
  },
  "gradebook": [
    {
      "student_id": 102,
      "student_username": "grace_hopper",
      "student_email": "hopper@navy.mil",
      "has_submitted": true,
      "attempts_count": 1,
      "best_status": "accepted",
      "best_score": 100.0,
      "latest_submission_at": "2026-11-10T14:22:00Z",
      "latest_submission_id": 41
    },
    {
      "student_id": 108,
      "student_username": "pending_student",
      "student_email": "pending@example.com",
      "has_submitted": false,
      "attempts_count": 0,
      "best_status": null,
      "best_score": 0.0,
      "latest_submission_at": null,
      "latest_submission_id": null
    }
  ]
}
```

---

## 7. Frontend Architecture & UI Walkthrough

The frontend integration lives entirely in clean, modular React components using the VS Code dark navy design system:

### 7.1 Student Dashboard Page (`StudentDashboardPage.jsx`)
- **Key Metrics Tiles:**
  - Assignments Completed (fraction + percentage progress bar).
  - Acceptance Rate (% of accepted submissions).
  - Total Marks Earned vs. Total Marks Possible.
  - Active Enrolled Classrooms count.
- **Proportional Outcome Distribution Bar:**
  - Multi-segmented colored bar reflecting the exact distribution of AC, WA, TLE, RE, and CE results.
  - Interactive legend with exact counts.
- **Enrolled Classrooms Grid:**
  - Dedicated cards for each course displaying the instructor's name, class join code, and individual marks earned.
- **Assignments Management Table:**
  - Direct filtering tabs: All, Pending, Submitted.
  - Due date indicator, `StatusBadge`, Best Score, and direct action buttons:
    - Pending labs display blue `Solve & Submit 💻` linking directly to `/assignments/<id>/submit`.
    - Completed labs display `History` (to review feedback) and `Resubmit` buttons.

### 7.2 Teacher Dashboard Page (`TeacherDashboardPage.jsx`)
- **Instructor Overview Row:**
  - Active Classrooms, Enrolled Students, Total Submissions, Overall Acceptance Rate %, Average Score %.
- **Classrooms Performance Grid:**
  - Course cards showing enrollment, published assignments, submission rates, and average grade.
  - One-click `View Analytics & Leaderboard 📈` button triggering an in-depth classroom modal.
- **Interactive Modals:**
  - **Classroom Modal:** Student leaderboard with medal rankings (🥇, 🥈, 🥉), email, completed labs count, total score, and assignment-level summary table.
  - **Assignment Modal:** Score distribution buckets (0–20%, 21–40%, etc.) and complete student roster gradebook with direct links to inspect student source code.
- **Recent Submissions Live Feed:**
  - Live log of recent student submissions across all courses with status badge, language badge, score, and link to code review.

### 7.3 Navigation & Routing Integration
- **`Navbar.jsx`**: Dynamically detects the user role and adds a persistent `📊 My Dashboard` (Student) or `📊 Instructor Dashboard` (Teacher) navigation shortcut.
- **`LoginPage.jsx`**: Automatically redirects students to `/dashboard` and teachers to `/teacher/dashboard` upon successful authentication.
- **`App.jsx`**: Provides role-based routing from root `/` to the appropriate dashboard.

---

## 8. File-by-File Technical Walkthrough

### Backend
1. **`backend/analytics/models.py`**
   - Documents the intentional architectural decision to avoid redundant analytics tables. Dynamic aggregations prevent out-of-sync caching bugs.
2. **`backend/analytics/serializers.py`**
   - Formulates clear, strongly typed serializer schemas:
     - `StudentDashboardSerializer`, `StudentClassroomSummarySerializer`, `StudentAssignmentProgressSerializer`.
     - `TeacherDashboardSerializer`, `TeacherClassroomSummarySerializer`, `TeacherRecentSubmissionSerializer`.
     - `ClassroomAnalyticsSerializer`, `ClassroomAssignmentStatsSerializer`, `LeaderboardStudentSerializer`.
     - `AssignmentAnalyticsSerializer`, `ScoreDistributionSerializer`, `GradebookEntrySerializer`.
3. **`backend/analytics/views.py`**
   - Implements four views with role-based permission checks and single-query ORM aggregations:
     - `StudentDashboardView` (enforces `IsStudentUser`, aggregates only student's approved memberships).
     - `TeacherDashboardView` (enforces `IsApprovedTeacherUser`, aggregates only teacher's owned classrooms).
     - `ClassroomAnalyticsView` (validates teacher ownership or returns 404, computes classroom leaderboard and assignment stats).
     - `AssignmentAnalyticsView` (validates assignment belongs to teacher's classroom or returns 404, computes 5-tier score histogram and student gradebook).
4. **`backend/analytics/urls.py`**
   - Routes:
     - `GET /api/analytics/student/dashboard/`
     - `GET /api/analytics/teacher/dashboard/`
     - `GET /api/analytics/classroom/<int:classroom_id>/`
     - `GET /api/analytics/assignment/<int:assignment_id>/`
5. **`backend/analytics/tests.py`**
   - 12 comprehensive unit tests verifying calculations, leaderboard ranking, score buckets, 0-submission edge cases, and RBAC security boundaries.

### Frontend
1. **`frontend/src/services/api.js`**
   - Added named functions: `getStudentDashboard()`, `getTeacherDashboard()`, `getClassroomAnalytics(id)`, `getAssignmentAnalytics(id)`.
2. **`frontend/src/pages/StudentDashboardPage.jsx`**
   - Complete student analytics dashboard with KPI cards, distribution bar, enrolled courses, and assignment action table.
3. **`frontend/src/pages/TeacherDashboardPage.jsx`**
   - Multi-classroom analytics cockpit with leaderboard modal, gradebook modal, score buckets, and recent submissions feed.
4. **`frontend/src/components/Navbar.jsx`**
   - Added dynamic role-specific dashboard link and brand redirect.
5. **`frontend/src/styles/global.css`**
   - Added utility classes: `.stats-grid`, `.stat-card`, `.progress-bar-bg`, `.dist-bar-wrapper`, `.modal-overlay`, `.modal-content`.
6. **`frontend/src/App.jsx`**
   - Registered `/dashboard` and `/teacher/dashboard` routes with automatic role redirection on root `/`.

---

## 9. Test Suite Verification (All 204 Tests Passing)

The complete LabCraft test suite was run across all 6 modules:

```powershell
python manage.py test accounts classrooms assignments submissions grader analytics -v 2
```

### Test Suite Execution Summary

| App Module | Tests Count | Status | Description |
|---|:---:|:---:|---|
| `accounts` | 33 | **PASSED** | Registration, JWT auth, teacher approval flow, role validation |
| `classrooms` | 36 | **PASSED** | Classroom CRUD, join codes, enrollment approvals, membership queries |
| `assignments` | 42 | **PASSED** | Assignment publishing, deadlines, language constraints, classroom scopes |
| `submissions` | 38 | **PASSED** | Source code submission, deadlines, teacher inspection, access control |
| `grader` | 43 | **PASSED** | Docker execution, safety constraints, test cases, hidden masking |
| `analytics` | 12 | **PASSED** | Dashboards, leaderboards, gradebooks, score buckets, RBAC isolation |
| **TOTAL** | **204** | **ALL PASSED (100%)** | Ran 204 tests in 239.384s — OK |

---

## 10. How to Push & Create a Pull Request

Follow these steps to submit the completed Module 6 feature branch for code review:

### Step 1: Check Git Status
```bash
git status
```
Ensure you are on branch `feature/analytics-dashboard` with all changes cleanly committed.

### Step 2: Push the Feature Branch to GitHub
```bash
git push -u origin feature/analytics-dashboard
```

### Step 3: Open the Pull Request on GitHub
1. Navigate to the GitHub repository: `https://github.com/<owner>/LabCraft`
2. Click **Compare & pull request** next to `feature/analytics-dashboard`.
3. Set **Base branch:** `develop` (DO NOT target `main`).
4. Set **Compare branch:** `feature/analytics-dashboard`.
5. Title: `feat(analytics): implement Module 6 — Analytics Dashboard & Final Integration`
6. Paste the summary from this document into the PR description.
7. Request team review and wait for approval before merging.
