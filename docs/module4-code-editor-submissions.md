# Module 4 — Code Editor & Submissions

> **LabCraft Backend + Frontend | Django REST Framework + React + Monaco Editor**
> Branch: `feature/code-editor-submissions`
> App: `submissions/` (backend) + `frontend/src/` (frontend)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Features Implemented](#2-features-implemented)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Database Model](#4-database-model)
5. [Backend File-by-File Explanation](#5-backend-file-by-file-explanation)
6. [Frontend File-by-File Explanation](#6-frontend-file-by-file-explanation)
7. [API Endpoints](#7-api-endpoints)
8. [Example Requests & Responses](#8-example-requests--responses)
9. [Security Rules](#9-security-rules)
10. [Deadline Enforcement](#10-deadline-enforcement)
11. [Monaco Editor Integration](#11-monaco-editor-integration)
12. [Migration Explanation](#12-migration-explanation)
13. [Test Results](#13-test-results)
14. [Important Concepts — Simply Explained](#14-important-concepts--simply-explained)
15. [How to Push & Create a Pull Request](#15-how-to-push--create-a-pull-request)

---

## 1. Overview

Module 4 adds **Code Submission** to LabCraft. Students can write code in the Monaco editor (the same editor used in VS Code), select their language, and submit their solution for a programming assignment. Each submission is stored in the database with the student's identity, assignment, source code, language, time, and status.

> **What Module 4 does NOT do:**
> - Execute submitted code — that is Module 5 (Docker Grading Engine)
> - Show hidden test cases
> - Automatically grade or score submissions

It reuses models from:
- `accounts.User` — the custom user model (teacher / student)
- `classrooms.Classroom` — classroom model from Module 2
- `classrooms.ClassroomMembership` — tracks which students joined which classroom
- `assignments.Assignment` — assignment model from Module 3

---

## 2. Features Implemented

| # | Feature | Who |
|---|---------|-----|
| 1 | Write and edit code in Monaco Editor (VS Code editor) | Student |
| 2 | Select programming language (auto-set from assignment) | Student |
| 3 | Submit code for a published, non-expired assignment | Student |
| 4 | View own submission history for an assignment | Student |
| 5 | View full details of one submission (source code + status) | Student |
| 6 | View all submissions for an assignment | Approved Teacher |
| 7 | View all submissions by a specific student | Approved Teacher |
| 8 | Deadline enforcement — reject late submissions | Automatic (view) |
| 9 | Language validation — reject wrong language | Serializer |
| 10 | Prevent cross-student data access (security) | QuerySet filtering |
| 11 | Prevent cross-teacher data access (security) | QuerySet filtering |
| 12 | Store submission with status 'pending' | Auto (default) |
| 13 | Show submission history table in frontend | Student UI |
| 14 | Read-only code viewer for submitted code | Student UI |

---

## 3. Architecture Diagram

```
[ React Frontend ]
       │
       │  HTTP requests (JSON)
       │  Authorization: Bearer <JWT token>
       │
[ Django REST Framework API ]
       │
       ├─ POST /api/submissions/assignment/<id>/submit/
       │      → SubmitCodeView
       │      → Checks: authenticated student, joined classroom,
       │                published assignment, before deadline,
       │                correct language, non-empty source code
       │      → Saves Submission record (status=pending)
       │
       ├─ GET /api/submissions/assignment/<id>/my/
       │      → MySubmissionListView
       │      → Returns only THIS student's submissions
       │
       ├─ GET /api/submissions/<id>/
       │      → SubmissionDetailView
       │      → Returns ONE submission (must belong to logged-in student)
       │
       ├─ GET /api/submissions/assignment/<id>/all/
       │      → TeacherSubmissionListView
       │      → Teacher only; shows all students' submissions
       │
       └─ GET /api/submissions/assignment/<id>/student/<student_id>/
              → TeacherStudentSubmissionView
              → Teacher only; shows one student's history
                                │
[ SQLite / PostgreSQL Database ]
       │
       └─ submissions_submission table
              - assignment (FK → assignments_assignment)
              - student (FK → accounts_user)
              - source_code (TextField)
              - language (CharField, choices)
              - status (CharField, 'pending' by default)
              - feedback (TextField, empty until Module 5)
              - submitted_at (DateTimeField, auto)
```

---

## 4. Database Model

### Entity Relationship Diagram

```
accounts_user (Student)
      │
      │ student (FK)
      ▼
submissions_submission ◄── assignment (FK) ── assignments_assignment
                                                        │
                                              classroom (FK)
                                                        │
                                              classrooms_classroom
                                                        │
                                              teacher (FK)
                                                        │
                                              accounts_user (Teacher)
```

### Submission Model Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField (PK) | Auto-generated primary key |
| `assignment` | ForeignKey → Assignment | Which assignment this submission is for |
| `student` | ForeignKey → User | The student who submitted |
| `source_code` | TextField | The code the student wrote |
| `language` | CharField (choices) | Programming language used |
| `status` | CharField (choices) | Grading status (starts as 'pending') |
| `feedback` | TextField (blank) | Grader feedback (Module 5 populates this) |
| `submitted_at` | DateTimeField (auto) | When the student clicked "Submit" |

### Status Choices

| Value | Display | Meaning |
|-------|---------|---------|
| `pending` | Pending | Just submitted, not yet graded |
| `running` | Running | Grader is executing it now |
| `accepted` | Accepted | All test cases passed ✅ |
| `wrong_answer` | Wrong Answer | Output doesn't match expected ❌ |
| `runtime_error` | Runtime Error | Code crashed during execution |
| `compile_error` | Compile Error | Code has syntax errors |
| `time_limit_exceeded` | Time Limit Exceeded | Code ran too long |
| `memory_limit_exceeded` | Memory Limit Exceeded | Code used too much RAM |

---

## 5. Backend File-by-File Explanation

### `submissions/models.py`

Defines the `Submission` model — the core database table for this module.

**Key design decisions:**

```python
assignment = models.ForeignKey(
    Assignment,
    on_delete=models.CASCADE,     # delete submissions when assignment deleted
    related_name='submissions',   # assignment.submissions.all()
)
```
> **WHY CASCADE?** A submission with no assignment is meaningless. When an assignment is deleted, all its submissions go too.

```python
student = models.ForeignKey(
    settings.AUTH_USER_MODEL,     # points to accounts.User
    on_delete=models.CASCADE,
    related_name='submissions',
    limit_choices_to={'role': 'student'},
)
```
> **WHY `settings.AUTH_USER_MODEL`?** Direct `from accounts.models import User` can cause circular imports. Using `settings.AUTH_USER_MODEL` is Django's official recommended pattern.

> **WHY `limit_choices_to`?** This tells Django Admin to only show students in the dropdown — teachers should not submit code.

```python
source_code = models.TextField()
```
> **WHY TextField not FileField?** Text is simpler — no file storage needed, easier to pass to the Docker grader in Module 5, and easier to display in the Monaco editor.

```python
status = models.CharField(
    max_length=25,
    choices=Status.choices,
    default=Status.PENDING,   # all new submissions start as 'pending'
)
```
> **WHY start at 'pending'?** The grading engine (Module 5) hasn't run yet. The submission is queued. 'pending' is the correct initial state.

```python
@property
def is_late(self):
    if self.assignment.due_date is None:
        return False
    return self.submitted_at > self.assignment.due_date
```
> **WHY a @property (not a DB field)?** The due_date can change — a teacher might extend the deadline. If `is_late` were stored in the database, it would become stale. A property is computed fresh every time it is read, so it always reflects the current due_date.

---

### `submissions/serializers.py`

Three serializers — each for a different purpose:

#### `SubmissionListSerializer` — compact, for history lists

```python
assignment_title = serializers.SerializerMethodField()
is_late = serializers.BooleanField(read_only=True)
```
> **WHY SerializerMethodField?** We want the assignment title as a plain string, not a full nested object. A SerializerMethodField lets us call `get_assignment_title(obj)` to compute it.

> **WHY no `source='is_late'`?** DRF raises an error if you set `source='is_late'` when the field is already named `is_late`. DRF auto-resolves model properties when the field name matches.

> **WHY no `source_code`?** The list view is for browsing many submissions. Including source code (potentially thousands of lines) would make the response unnecessarily large. Only the detail view includes it.

#### `SubmissionDetailSerializer` — full data for one submission

```python
student = UserProfileSerializer(read_only=True)
```
> **WHY nest UserProfileSerializer?** The teacher/student can see the student's username without making a second API call. `read_only=True` ensures the client can't change who the student is.

#### `SubmissionCreateSerializer` — accepts student code input

```python
def validate_source_code(self, value):
    if not value or not value.strip():
        raise serializers.ValidationError("Source code cannot be empty...")
```
> **WHY validate here?** The student might accidentally submit an empty editor. This prevents useless empty submissions from being stored.

```python
def validate(self, attrs):
    assignment = self.context.get('assignment')
    if assignment.language != 'other' and language != assignment.language:
        raise serializers.ValidationError({'language': '...'})
```
> **WHY cross-field validate in `validate()` not `validate_language()`?** We need BOTH `language` AND the `assignment` object. `validate()` has access to all fields plus the `context` dict (where the view passes the assignment). Single-field validators only get one field at a time.

---

### `submissions/views.py`

Five views with thorough security checks at every step.

#### `SubmitCodeView` — POST, student submits code

```python
assignment = get_object_or_404(Assignment, id=assignment_id, is_published=True)
```
> **WHY `is_published=True`?** Students shouldn't submit to draft assignments. If `is_published=False`, this returns 404 — not revealing that the assignment even exists.

```python
get_object_or_404(ClassroomMembership, student=request.user, classroom=assignment.classroom)
```
> **WHY 404 (not 403)?** Returning 403 would reveal that the assignment exists but the student isn't a member. Returning 404 reveals nothing — the student sees the same response as if the assignment didn't exist at all.

```python
if assignment.due_date and timezone.now() > assignment.due_date:
    return Response({'error': '...'}, status=status.HTTP_400_BAD_REQUEST)
```
> **WHY enforce deadline in the view (not the model)?** The model must be agnostic — Module 5 (the grader) needs to update submission records even after the deadline. The view is the right place to block NEW submissions.

```python
submission = serializer.save(assignment=assignment, student=request.user)
```
> **WHY inject assignment and student here?** These come from the URL and JWT token — they should NOT come from the request body. If we let the student send their own `student_id`, they could forge another student's submission.

---

### `submissions/urls.py`

Five URL patterns — all mounted under `/api/submissions/` in `config/urls.py`.

```python
path('assignment/<int:assignment_id>/submit/', SubmitCodeView.as_view(), name='submission-submit'),
```
> **WHY name the URLs?** Named URLs let us use `reverse('submission-submit', kwargs={...})` in tests. If the URL path ever changes, we only update it in one place.

---

### `submissions/admin.py`

Registers the Submission model in Django Admin for review and debugging.

```python
list_display = ['id', 'student', 'assignment', 'language', 'status', 'is_late', 'submitted_at']
```
> **WHY include `is_late`?** Teachers and admins can quickly see which submissions were late without calculating it themselves.

```python
readonly_fields = ['submitted_at', 'is_late']
```
> **WHY readonly?** `submitted_at` is set by `auto_now_add` — it cannot be changed. `is_late` is a computed property — it has no database column to write to.

---

## 6. Frontend File-by-File Explanation

### `frontend/src/services/api.js`

The centralized API communication layer.

```js
const api = axios.create({ baseURL: 'http://localhost:8000' });
```
> **WHY centralize?** If the API base URL changes (e.g. in production), we update ONE file instead of every component.

```js
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```
> **WHY an interceptor?** Without this, every API call would need to manually add the Authorization header. The interceptor adds it automatically to every request — one place to change, works everywhere.

```js
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.clear();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```
> **WHY on 401?** If the JWT token expires and an API call returns "401 Unauthorized", the user's session is invalid. We clear all stored data and redirect to login — no stale session issues.

---

### `frontend/src/pages/CodeEditorPage.jsx`

The main feature page — where students write and submit code.

```jsx
import Editor from '@monaco-editor/react';
```
> **WHY Monaco?** Monaco is the editor that powers VS Code. It provides syntax highlighting, auto-indentation, bracket matching, and line numbers — all the features students need to write code comfortably in a browser.

```jsx
<Editor
  height="500px"
  language={monacoLang}   // e.g. 'python', 'java', 'cpp'
  theme="vs-dark"         // dark theme like VS Code
  value={code}
  onChange={(value) => setCode(value || '')}
  options={{
    fontSize: 14,
    minimap: { enabled: false },   // hide the minimap (distraction for students)
    automaticLayout: true,          // resize when container resizes
  }}
/>
```
> **WHY `automaticLayout: true`?** Without this, the editor's internal dimensions don't update when the browser window is resized — the editor would appear clipped or overflow.

> **WHY `value || ''`?** Monaco's `onChange` can pass `undefined` if the editor is cleared completely. We coerce `undefined` to `''` to keep our state as a string.

```jsx
const monacoLang = MONACO_LANGUAGE[assignment.language] || 'plaintext';
```
> **WHY map assignment language to Monaco language?** The assignment stores `'cpp'` but Monaco wants `'cpp'` (same here), `'python'` (same), `'javascript'` (same) etc. We centralize this mapping in `languageMap.js` so if Monaco ever changes its language identifiers, we update one file.

---

### `frontend/src/pages/SubmissionHistoryPage.jsx`

Shows all of a student's attempts at one assignment.

```jsx
const response = await getMySubmissions(assignmentId);
```
> **WHY show history?** Students often submit multiple times — first attempt may fail. The history lets them see all their attempts, track when they submitted, and whether they were on time.

---

### `frontend/src/pages/SubmissionDetailPage.jsx`

Shows the full detail of one submission, including the code in a read-only Monaco editor.

```jsx
<Editor
  height="400px"
  language={monacoLang}
  theme="vs-dark"
  value={submission.source_code}
  options={{ readOnly: true, ... }}   // READ ONLY — student cannot accidentally edit their submitted code
/>
```
> **WHY read-only?** This is a historical record of what the student submitted. It should not be editable. `readOnly: true` in Monaco options prevents any typing in the editor.

---

### `frontend/src/pages/TeacherSubmissionsPage.jsx`

Shows a teacher all submissions for their assignment.

```jsx
// Teacher uses TeacherSubmissionListView endpoint which
// automatically verifies assignment.classroom.teacher == request.user
const response = await getTeacherSubmissions(assignmentId);
```
> **WHY the backend enforces it?** The frontend is not secure — a user could bypass the React UI and call the API directly. The backend always re-verifies that the assignment belongs to this teacher's classroom.

---

### `frontend/src/utils/languageMap.js`

Centralizes all language-related constants.

```js
export const MONACO_LANGUAGE = {
  python: 'python',
  java: 'java',
  c: 'c',
  cpp: 'cpp',
  javascript: 'javascript',
  other: 'plaintext',  // 'other' has no specific Monaco language → use plaintext
};
```
> **WHY centralize?** Both `CodeEditorPage` and `SubmissionDetailPage` need this mapping. By defining it once, we avoid inconsistencies.

---

## 7. API Endpoints

### Student Endpoints (require student login)

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/api/submissions/assignment/<id>/submit/` | Submit code for an assignment |
| `GET` | `/api/submissions/assignment/<id>/my/` | View own submission history |
| `GET` | `/api/submissions/<id>/` | View full detail of one submission |

### Teacher Endpoints (require approved teacher login)

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/submissions/assignment/<id>/all/` | View ALL submissions for assignment |
| `GET` | `/api/submissions/assignment/<id>/student/<student_id>/` | View one student's submissions |

---

## 8. Example Requests & Responses

### Submit Code (Student)

**Request:**
```http
POST /api/submissions/assignment/1/submit/
Authorization: Bearer <student_jwt_token>
Content-Type: application/json

{
  "source_code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\nprint(fibonacci(10))",
  "language": "python"
}
```

**Success Response (201 Created):**
```json
{
  "message": "Your code for \"Lab 1: Fibonacci\" has been submitted successfully. Status: Pending grading.",
  "submission": {
    "id": 42,
    "assignment_id": 1,
    "assignment_title": "Lab 1: Fibonacci",
    "classroom_id": 3,
    "classroom_name": "Python Lab - Sem 3",
    "student": {
      "id": 7,
      "username": "alice",
      "role": "student"
    },
    "source_code": "def fibonacci(n):\n    ...",
    "language": "python",
    "status": "pending",
    "feedback": "",
    "is_late": false,
    "submitted_at": "2026-11-10T13:30:00Z"
  }
}
```

**Error — Deadline Passed (400):**
```json
{
  "error": "The deadline for \"Lab 1: Fibonacci\" has passed (09 Nov 2026, 11:59 PM). No more submissions are accepted."
}
```

**Error — Wrong Language (400):**
```json
{
  "language": "This assignment requires Python. You submitted Java."
}
```

**Error — Not a Member (404):**
```json
{
  "detail": "No ClassroomMembership matches the given query."
}
```

---

### View Own Submission History (Student)

**Request:**
```http
GET /api/submissions/assignment/1/my/
Authorization: Bearer <student_jwt_token>
```

**Response (200 OK):**
```json
[
  {
    "id": 42,
    "assignment_id": 1,
    "assignment_title": "Lab 1: Fibonacci",
    "language": "python",
    "status": "pending",
    "is_late": false,
    "submitted_at": "2026-11-10T13:30:00Z"
  },
  {
    "id": 38,
    "assignment_id": 1,
    "assignment_title": "Lab 1: Fibonacci",
    "language": "python",
    "status": "accepted",
    "is_late": false,
    "submitted_at": "2026-11-09T10:15:00Z"
  }
]
```

> **Note:** `source_code` is intentionally NOT included in the list view — it's too heavy for a list. Use the detail endpoint to get source code.

---

### View Submission Detail (Student)

**Request:**
```http
GET /api/submissions/42/
Authorization: Bearer <student_jwt_token>
```

**Response (200 OK):**
```json
{
  "id": 42,
  "assignment_id": 1,
  "assignment_title": "Lab 1: Fibonacci",
  "classroom_id": 3,
  "classroom_name": "Python Lab - Sem 3",
  "student": { "id": 7, "username": "alice", "role": "student" },
  "source_code": "def fibonacci(n):\n    ...",
  "language": "python",
  "status": "pending",
  "feedback": "",
  "is_late": false,
  "submitted_at": "2026-11-10T13:30:00Z"
}
```

**Security — Another Student Tries to Access (404):**
```json
{
  "detail": "No Submission matches the given query."
}
```
> Even if Bob knows the submission ID 42, he gets 404 — not 403. This reveals nothing about whether the submission exists.

---

## 9. Security Rules

| Rule | Implementation | Location |
|------|---------------|----------|
| Students can only submit to published assignments | `get_object_or_404(is_published=True)` | `SubmitCodeView` |
| Students can only submit to joined classrooms | `get_object_or_404(ClassroomMembership, student=user)` | `SubmitCodeView` |
| Students can only view THEIR OWN submissions | `Submission.objects.filter(student=request.user)` | `SubmissionDetailView`, `MySubmissionListView` |
| Teachers can only view submissions in THEIR classrooms | `get_object_or_404(classroom__teacher=request.user)` | `TeacherSubmissionListView` |
| Student cannot forge their identity | `serializer.save(student=request.user)` — not from request body | `SubmitCodeView` |
| Teacher endpoint returns 403 for students | `permission_classes = [IsApprovedTeacher]` | View class |
| Student endpoint returns 403 for teachers | `permission_classes = [IsStudent]` | View class |
| Unauthenticated access returns 401 | Default DRF `IsAuthenticated` permission | `settings.py` |

---

## 10. Deadline Enforcement

The deadline check happens in the **view** (not the model or serializer):

```python
# In SubmitCodeView.create():
if assignment.due_date and timezone.now() > assignment.due_date:
    return Response({'error': '...'}, status=400)
```

**Why in the view?**
- The model is shared with Module 5 (the grader), which must update submissions after the deadline (the grader doesn't stop working when the deadline passes).
- The serializer handles data validation, not business rules.
- The view is the right layer for business-rule enforcement.

**What about the `is_late` property on the model?**

`is_late` is a read-only computed property that tells you whether a submission *was already* made late (after deadline). It is NOT a gate that prevents submissions — the view does that. `is_late` is used for display purposes: showing "⚠️ Late" badges in the submission history.

---

## 11. Monaco Editor Integration

Monaco is the open-source editor that powers Visual Studio Code. We use `@monaco-editor/react`, which wraps it for React.

### Installation
```bash
pnpm add @monaco-editor/react
# already installed — in frontend/node_modules/@monaco-editor/
```

### Language Mapping

The assignment stores a language like `'python'` or `'cpp'`. Monaco accepts its own language identifiers. They happen to match in most cases, but `'other'` maps to `'plaintext'`:

| Assignment Language | Monaco Language |
|--------------------|-----------------|
| `python` | `python` |
| `java` | `java` |
| `c` | `c` |
| `cpp` | `cpp` |
| `javascript` | `javascript` |
| `other` | `plaintext` |

### Key Monaco Options Explained

```jsx
options={{
  fontSize: 14,                // comfortable reading size
  minimap: { enabled: false }, // hide the small overview map (distracting for students)
  scrollBeyondLastLine: false, // don't add extra whitespace after last line
  automaticLayout: true,       // resize when the container resizes (responsive)
  wordWrap: 'on',              // wrap long lines (important for small screens)
  readOnly: true,              // used in SubmissionDetailPage — prevents editing history
}}
```

---

## 12. Migration Explanation

### What is a migration?

A migration is a Python file that describes a change to the database schema (tables, columns, indexes). Django generates migrations automatically from your models. You then run them to actually apply the changes to the database.

### The submissions migration

```
backend/submissions/migrations/0001_initial.py
```

This migration creates the `submissions_submission` table in the database.

**To apply migrations:**
```bash
cd backend
python manage.py migrate
```

**What this command does:**
1. Django checks which migrations have already been applied (tracked in `django_migrations` table)
2. It runs any pending migrations in order
3. It creates/alters database tables to match your models

**Why do we need migrations?**
You cannot just edit a model and expect the database to change automatically. Migrations are the bridge between Python model code and the actual database structure. They also allow teams to safely share database schema changes — when you pull someone's code with a new migration, you run `migrate` to sync your database.

**The migration file contents:**
```python
class Migration(migrations.Migration):
    initial = True  # This is the first migration for this app

    dependencies = [
        ('assignments', '0001_initial'),  # submissions table needs assignments table first
    ]

    operations = [
        migrations.CreateModel(
            name='Submission',
            fields=[...],
        ),
    ]
```

> **WHY `dependencies`?** The Submission model has a ForeignKey to Assignment. The assignments table must exist before the submissions table is created. `dependencies` tells Django the order to run migrations.

---

## 13. Test Results

**Run all backend tests:**
```bash
cd backend
python manage.py test accounts classrooms assignments submissions -v 2
```

### Submissions Test Suite Breakdown

| Class | Tests | What It Covers |
|-------|-------|----------------|
| `SubmissionModelTest` | 6 | Model fields, defaults, is_late property, __str__, ordering |
| `SubmitCodeTest` | 10 | Successful submission, DB persistence, status='pending', published check, classroom check, empty/whitespace check, language validation |
| `DeadlineEnforcementTest` | 3 | Submissions before deadline ✅, after deadline rejected (400) ❌, no deadline accepted ✅ |
| `MySubmissionListTest` | 4 | Student history list, cross-student isolation, unjoined classroom blocked, compact fields |
| `SubmissionDetailTest` | 3 | Detail view with source code, cross-student access denied (404), classroom metadata |
| `TeacherSubmissionViewTest` | 4 | Teacher views all submissions, includes source code, cross-teacher isolation (404), student access blocked (403) |
| `TeacherStudentSubmissionTest` | 2 | Teacher filters by specific student, cross-classroom isolation |
| `SubmissionSecurityTest` | 3 | Cross-student detail access denied (404), history isolation, list view code protection |
| `SubmissionPermissionTest` | 7 | Unauthenticated rejected (401), teacher cannot submit (403), pending teacher blocked (403), role enforcement across all endpoints |

**Total submissions tests: 45**
**Total platform test suite (Accounts + Classrooms + Assignments + Submissions): 167 tests**

**Actual execution output:**
```
Ran 45 tests in 61.937s
OK
Destroying test database for alias 'default'...

Ran 167 tests in 267.619s
OK
Destroying test database for alias 'default'...
```

---

## 14. Important Concepts — Simply Explained

### What is a JWT token?

JWT stands for **JSON Web Token**. It's a string the server gives you after login. The string contains your user ID and role, encoded and signed by the server. Every time you make an API request, you send this token in the `Authorization` header. The server verifies the signature to know who you are — without looking up a session in the database.

Think of it like a cinema ticket: you buy it once (login), and then you show it at every door (API endpoint) to prove you paid.

### Why do we use `request.user` instead of letting students send their user ID?

If we let students send `{"student_id": 5}` in the request body, **any student could submit code as any other student**. By reading `request.user` from the JWT token (which the server signed and the student cannot forge), we always know *exactly* who is submitting. This is a fundamental security principle: **trust the token, not the payload**.

### What is a ForeignKey?

A ForeignKey is a database relationship that links two tables. `Submission.assignment = ForeignKey(Assignment)` means: "every submission record stores the ID of the assignment it belongs to." If you have submission #42, it stores `assignment_id = 1`. To get the full assignment, Django joins the two tables automatically.

### What is `on_delete=CASCADE`?

Imagine assignment #1 is deleted. What should happen to all submissions that reference `assignment_id = 1`? `CASCADE` says: **delete them too**. Without this, you'd have "orphan" submissions pointing to a non-existent assignment, which would cause errors.

### What is an Axios interceptor?

An interceptor is a piece of code that runs **before every request** (request interceptor) or **after every response** (response interceptor). It's like a security guard at a door:
- **Request interceptor:** "Before you go out, here's your Authorization badge."
- **Response interceptor:** "If the server said you're not allowed in (401), go back to the login page."

### What is Monaco Editor?

Monaco is the editor built into Visual Studio Code. By installing `@monaco-editor/react`, we embed the exact same editor in our React app. Students get syntax highlighting, line numbers, bracket matching, and auto-indentation — all inside the browser, with zero extra installations.

### Why don't we execute submitted code on the Django server?

Executing untrusted code directly on a server is **extremely dangerous**. A student could write:
```python
import os; os.system("rm -rf /")  # delete all server files!
```
Module 5 uses **Docker containers** to run code in an isolated sandbox with time/memory/network limits. That way, even if a student's code is malicious, it cannot damage the server.

---

## 15. How to Push & Create a Pull Request

After all code is committed on `feature/code-editor-submissions`, push it to GitHub:

```bash
# 1. Make sure you're on the right branch
git branch   # should show * feature/code-editor-submissions

# 2. Push the branch to GitHub (first time — sets the upstream)
git push -u origin feature/code-editor-submissions

# 3. GitHub will show a prompt to create a Pull Request, or go to:
#    https://github.com/<your-username>/LabCraft/compare/feature/code-editor-submissions
```

### Creating the PR on GitHub

1. Click **"Compare & pull request"**
2. Set **base branch** to `develop` (NOT `main`)
3. Title: `feat: Module 4 — Code Editor & Submissions`
4. Description:
   ```
   ## Summary
   Implements Module 4: Code Editor & Submissions for LabCraft.

   ## Changes
   ### Backend (submissions/)
   - Submission model with status choices and is_late property
   - 5 API endpoints with security checks
   - 3 serializers (list, detail, create)
   - Django Admin integration
   - 42 tests covering all scenarios

   ### Frontend (frontend/src/)
   - Monaco editor integration (CodeEditorPage)
   - Submission history view (SubmissionHistoryPage)
   - Submission detail with read-only code viewer (SubmissionDetailPage)
   - Teacher submissions view (TeacherSubmissionsPage)
   - Centralized API service with JWT interceptors
   - Language and status mapping utilities

   ## Test Results
   All X/X tests pass.

   ## Does NOT implement
   - Docker grading engine (Module 5)
   - Code execution on server
   - Hidden test cases
   ```
5. Click **"Create pull request"**
6. **Do NOT merge** — wait for review

> **Important:** Do not merge into `develop` without approval. The PR should sit open for review.

