# Module 3 — Assignment Management

> **LabCraft Backend | Django REST Framework**
> Branch: `feature/assignment-management`
> App: `assignments/`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Features Implemented](#2-features-implemented)
3. [Database Model](#3-database-model)
4. [File-by-File Explanation](#4-file-by-file-explanation)
5. [API Endpoints](#5-api-endpoints)
6. [Example Requests & Responses](#6-example-requests--responses)
7. [Draft / Published System](#7-draft--published-system)
8. [Due Date & Status Logic](#8-due-date--status-logic)
9. [Student Access Control](#9-student-access-control)
10. [Migration Explanation](#10-migration-explanation)
11. [Test Results](#11-test-results)
12. [How to Push & Create a Pull Request](#12-how-to-push--create-a-pull-request)

---

## 1. Overview

Module 3 adds **Assignment Management** to LabCraft. Teachers can create programming assignments inside their classrooms. Students can view published assignments only in classrooms they have joined.

This module deliberately does **not** implement:
- Code submission (Module 4)
- Automatic grading (Module 5)
- Assignment analytics (Module 6)

It reuses models from:
- `accounts.User` — the custom user model (teacher / student)
- `classrooms.Classroom` — the classroom model from Module 2
- `classrooms.ClassroomMembership` — tracks which students are in which classroom

---

## 2. Features Implemented

| # | Feature | Who |
|---|---------|-----|
| 1 | Create assignment in own classroom | Approved Teacher |
| 2 | Edit and delete own assignments | Approved Teacher |
| 3 | View all assignments in a classroom (draft + published) | Approved Teacher |
| 4 | Draft / publish toggle (`is_published`) | Approved Teacher |
| 5 | View published assignments in joined classrooms | Student |
| 6 | View full assignment details | Student (joined classrooms only) |
| 7 | Block student from seeing unjoined classroom assignments | Automatic (via queryset) |
| 8 | Block draft assignments from students | Automatic (via queryset) |
| 9 | Input validation (title, marks, due date, language, difficulty) | Serializer |
| 10 | Role-based permissions | `IsApprovedTeacher`, `IsStudent` |

---

## 3. Database Model

### Entity Relationship Diagram

```
accounts_user (Teacher)
      │
      │ created_by (FK)
      ▼
assignments_assignment ◄──── classroom (FK) ──── classrooms_classroom
      │                                                   │
      │                                     students (M2M via ClassroomMembership)
      │                                                   │
      │                                        accounts_user (Student)
      │
   Fields:
      - title (CharField)
      - description (TextField)
      - instructions (TextField)
      - due_date (DateTimeField, nullable)
      - max_marks (PositiveIntegerField)
      - language (CharField, choices)
      - difficulty (CharField, choices)
      - is_published (BooleanField)
      - created_at (DateTimeField, auto)
      - updated_at (DateTimeField, auto)
      
   Computed (@property):
      - is_past_due → True if due_date has passed
      - status → 'draft' | 'open' | 'closed'
```

### Language Choices

| Value | Display |
|-------|---------|
| `python` | Python |
| `java` | Java |
| `c` | C |
| `cpp` | C++ |
| `javascript` | JavaScript |
| `other` | Other |

### Difficulty Choices

| Value | Display |
|-------|---------|
| `easy` | Easy |
| `medium` | Medium |
| `hard` | Hard |

---

## 4. File-by-File Explanation

### `assignments/models.py`

Defines the `Assignment` model — the core data table.

**Key design decisions:**

```python
classroom = models.ForeignKey(
    Classroom,
    on_delete=models.CASCADE,    # delete assignments when classroom deleted
    related_name='assignments',  # classroom.assignments.all()
)
```
> **WHY CASCADE?** An assignment with no classroom is orphaned and useless. If a classroom is deleted, all its assignments go with it.

```python
created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,    # NOT direct User import — avoids circular imports
    on_delete=models.CASCADE,
    related_name='created_assignments',
)
```
> **WHY `settings.AUTH_USER_MODEL`?** Direct `from accounts.models import User` can cause circular imports between Django apps. Using `settings.AUTH_USER_MODEL` is the officially recommended Django pattern.

```python
is_published = models.BooleanField(default=False)
```
> **WHY default False?** Teachers often prepare assignments in advance. Starting as draft means students never accidentally see half-finished assignments.

```python
@property
def is_past_due(self):
    if self.due_date is None:
        return False
    return timezone.now() > self.due_date  # timezone-aware comparison
```
> **WHY `timezone.now()` not `datetime.now()`?** Django stores datetimes with timezone info (`USE_TZ=True`). Comparing a timezone-aware datetime with a naive one raises a `TypeError`. Always use `timezone.now()` in Django projects.

```python
@property
def status(self):
    if not self.is_published:
        return 'draft'
    if self.is_past_due:
        return 'closed'
    return 'open'
```
> **WHY a property?** The status is a computed value — it changes over time as the deadline passes. Storing it in the database would require a background job to update it. A property is always up-to-date and requires zero extra DB space.

---

### `assignments/serializers.py`

Three serializers following the same pattern as `classrooms/serializers.py`.

#### `AssignmentListSerializer` — compact, for lists

```python
status = serializers.CharField(read_only=True)
is_past_due = serializers.BooleanField(read_only=True)
```
> **WHY no `source=` argument?** DRF raises `AssertionError: The `source` argument is not meaningful when applied to a `SerializerMethodField`... field name and source name are identical` if you write `source='status'` when the field is already called `status`. DRF resolves model properties automatically when field name matches.

#### `AssignmentDetailSerializer` — full data for one assignment

```python
created_by = UserProfileSerializer(read_only=True)
```
> **WHY nest the serializer?** The frontend can display the teacher's name without making a second API call. `read_only=True` ensures the client can't forge the creator.

#### `AssignmentWriteSerializer` — accepts teacher input

```python
def validate_due_date(self, value):
    if value is not None and self.instance is None:  # only on CREATE
        if value <= timezone.now():
            raise serializers.ValidationError(...)
```
> **WHY check `self.instance`?** `self.instance` is `None` during POST (create) and an `Assignment` object during PATCH (update). We only reject past dates on create — teachers should be able to set past dates on update (e.g. to close an assignment retroactively).

---

### `assignments/views.py`

Four views following the same pattern as `classrooms/views.py`.

#### `TeacherAssignmentListCreateView`

```python
def get_queryset(self):
    classroom_id = self.kwargs['classroom_id']
    return Assignment.objects.filter(
        classroom__id=classroom_id,
        classroom__teacher=self.request.user  # security: only own classrooms
    )
```
> **WHY filter by `classroom__teacher`?** Without this, a teacher could list (or create) assignments in any classroom by guessing the ID. The double underscore `__` crosses the FK relationship.

```python
def create(self, request, *args, **kwargs):
    classroom = get_object_or_404(Classroom, id=classroom_id, teacher=request.user)
    assignment = serializer.save(classroom=classroom, created_by=request.user)
```
> **WHY inject classroom and created_by?** These fields are NOT in `AssignmentWriteSerializer`. The teacher can only send: title, description, instructions, due_date, max_marks, language, difficulty, is_published. They can never forge who the creator is or which classroom it belongs to.

> **WHY only call `serializer.save()` once?** If you define both `create()` and `perform_create()` and both call `serializer.save()`, the assignment is saved to the database twice — a subtle bug that can cause duplicate data.

#### `StudentAssignmentListView`

```python
membership = get_object_or_404(
    ClassroomMembership,
    student=self.request.user,
    classroom__id=classroom_id
)
return Assignment.objects.filter(classroom=membership.classroom, is_published=True)
```
> **WHY `get_object_or_404` on membership?** If the student hasn't joined, the lookup fails and returns 404. We use 404 (not 403) because 403 would reveal "this classroom exists, you just can't access it." 404 reveals nothing.

#### `StudentAssignmentDetailView`

```python
def get_queryset(self):
    return Assignment.objects.filter(
        is_published=True,
        classroom__students=self.request.user  # M2M lookup
    )
```
> **WHY `classroom__students=request.user`?** `students` is the M2M field on `Classroom` that connects to users via `ClassroomMembership`. Django's ORM lets us filter across M2M relationships with the double underscore syntax. This single filter replaces what would otherwise be a manual membership check.

---

### `assignments/urls.py`

```python
urlpatterns = [
    path('classroom/<int:classroom_id>/',          TeacherAssignmentListCreateView...),
    path('<int:pk>/',                              TeacherAssignmentDetailView...),
    path('classroom/<int:classroom_id>/student/',  StudentAssignmentListView...),
    path('<int:pk>/student/',                      StudentAssignmentDetailView...),
]
```
> **WHY put `classroom/<id>/student/` before `<pk>/student/`?** Django matches URLs in order. If `<pk>/student/` came first, Django would try to interpret `classroom` as an integer pk and fail. By listing the more specific pattern first, we avoid this ambiguity.

---

### `assignments/admin.py`

```python
@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'classroom', 'created_by', ...]
    readonly_fields = ['created_at', 'updated_at', 'is_past_due', 'status']
```
> **WHY `is_past_due` and `status` in `readonly_fields`?** These are `@property` values — they're computed at runtime, not stored in the database. Django Admin can display them but cannot let you edit them (there's no column to save to).

---

### `assignments/apps.py`

```python
class AssignmentsConfig(AppConfig):
    name = 'assignments'
    verbose_name = 'Assignment Management'
```
> **WHY set `verbose_name`?** This is the display name shown in the Django Admin panel sidebar. Without it, Admin shows the raw app name `assignments`.

---

## 5. API Endpoints

All endpoints are mounted under `/api/assignments/`.

### Teacher Endpoints (require `IsApprovedTeacher`)

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/assignments/classroom/<classroom_id>/` | List all assignments (draft + published) in teacher's classroom |
| `POST` | `/api/assignments/classroom/<classroom_id>/` | Create a new assignment in that classroom |
| `GET` | `/api/assignments/<id>/` | View full details of a specific assignment |
| `PATCH` | `/api/assignments/<id>/` | Partially update an assignment (e.g. change title or publish) |
| `DELETE` | `/api/assignments/<id>/` | Delete an assignment |

### Student Endpoints (require `IsStudent`)

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/assignments/classroom/<classroom_id>/student/` | List published assignments in a classroom the student has joined |
| `GET` | `/api/assignments/<id>/student/` | View full details of one published assignment |

### Permission Rules Summary

| Endpoint | Unauthenticated | Student | Pending Teacher | Approved Teacher |
|----------|-----------------|---------|-----------------|------------------|
| Teacher list/create | 401 | 403 | 403 | ✅ |
| Teacher detail/CRUD | 401 | 403 | 403 | ✅ (own only) |
| Student list | 401 | ✅ (joined only) | 403 | 403 |
| Student detail | 401 | ✅ (joined + published) | 403 | 403 |

---

## 6. Example Requests & Responses

### Create an Assignment (Teacher)

**Request:**
```http
POST /api/assignments/classroom/3/
Authorization: Bearer <teacher_jwt_token>
Content-Type: application/json

{
  "title": "Lab 1: Fibonacci Sequence",
  "description": "Implement Fibonacci using recursion and iteration.",
  "instructions": "1. Write a recursive fib(n) function.\n2. Write an iterative version.\n3. Compare their time complexity.",
  "due_date": "2026-12-01T23:59:00+05:30",
  "max_marks": 100,
  "language": "python",
  "difficulty": "medium",
  "is_published": false
}
```

**Response (201 Created):**
```json
{
  "message": "Assignment \"Lab 1: Fibonacci Sequence\" created successfully.",
  "assignment": {
    "id": 1,
    "title": "Lab 1: Fibonacci Sequence",
    "description": "Implement Fibonacci using recursion and iteration.",
    "instructions": "1. Write a recursive fib(n) function...",
    "classroom_id": 3,
    "classroom_name": "Python Lab - Sem 3",
    "created_by": {
      "id": 5,
      "username": "prof_sharma",
      "first_name": "Ravi",
      "last_name": "Sharma",
      "role": "teacher",
      "is_approved": true
    },
    "language": "python",
    "difficulty": "medium",
    "due_date": "2026-12-01T23:59:00+05:30",
    "max_marks": 100,
    "is_published": false,
    "status": "draft",
    "is_past_due": false,
    "created_at": "2026-11-10T10:00:00+05:30",
    "updated_at": "2026-11-10T10:00:00+05:30"
  }
}
```

---

### List Assignments (Teacher)

**Request:**
```http
GET /api/assignments/classroom/3/
Authorization: Bearer <teacher_jwt_token>
```

**Response (200 OK):**
```json
[
  {
    "id": 2,
    "title": "Lab 2: Sorting Algorithms",
    "description": "Implement bubble sort and merge sort.",
    "classroom_id": 3,
    "classroom_name": "Python Lab - Sem 3",
    "language": "python",
    "difficulty": "hard",
    "due_date": "2026-11-20T23:59:00+05:30",
    "max_marks": 50,
    "is_published": true,
    "status": "open",
    "is_past_due": false,
    "created_at": "2026-11-08T09:00:00+05:30"
  },
  {
    "id": 1,
    "title": "Lab 1: Fibonacci Sequence",
    "is_published": false,
    "status": "draft",
    ...
  }
]
```

> Note: Teacher sees BOTH draft and published. Students can only see published.

---

### Publish an Assignment (Teacher PATCH)

**Request:**
```http
PATCH /api/assignments/1/
Authorization: Bearer <teacher_jwt_token>
Content-Type: application/json

{
  "is_published": true
}
```

**Response (200 OK):**
```json
{
  "message": "Assignment \"Lab 1: Fibonacci Sequence\" updated successfully.",
  "assignment": {
    "id": 1,
    "is_published": true,
    "status": "open",
    ...
  }
}
```

---

### List Assignments (Student)

**Request:**
```http
GET /api/assignments/classroom/3/student/
Authorization: Bearer <student_jwt_token>
```

**Response (200 OK):** *(only published assignments)*
```json
[
  {
    "id": 2,
    "title": "Lab 2: Sorting Algorithms",
    "is_published": true,
    "status": "open",
    "is_past_due": false,
    ...
  }
]
```

---

### Student Accesses Unjoined Classroom

**Request:**
```http
GET /api/assignments/classroom/99/student/
Authorization: Bearer <student_jwt_token>
```

**Response (404 Not Found):**
```json
{
  "detail": "No ClassroomMembership matches the given query."
}
```

---

### Delete Assignment (Teacher)

**Request:**
```http
DELETE /api/assignments/1/
Authorization: Bearer <teacher_jwt_token>
```

**Response (200 OK):**
```json
{
  "message": "Assignment \"Lab 1: Fibonacci Sequence\" has been deleted."
}
```

---

## 7. Draft / Published System

The `is_published` field controls who can see an assignment:

```
is_published = False  →  DRAFT
  ✅ Teacher who created it can see it
  ❌ Students cannot see it
  status → "draft"

is_published = True  →  PUBLISHED
  ✅ Teacher can see it
  ✅ Students in the classroom can see it
  status → "open" (if deadline hasn't passed)
  status → "closed" (if deadline has passed)
```

**Flow:**
1. Teacher creates assignment → `is_published=False` (draft)
2. Teacher writes title, instructions, sets due_date
3. When ready → Teacher PATCHes `{"is_published": true}`
4. Students immediately see the assignment in their list
5. After `due_date` passes → `status` becomes `"closed"` (computed automatically)

This lets teachers prepare assignments well in advance without students seeing them.

---

## 8. Due Date & Status Logic

The `status` and `is_past_due` values are **computed properties** on the model:

```
No due_date set:
  is_past_due → False (never expires)
  status → "open" (if published) or "draft"

due_date in future:
  is_past_due → False
  status → "open" (if published) or "draft"

due_date in past:
  is_past_due → True
  status → "closed" (if published) or "draft"
```

**Key technical point:** We use `timezone.now()` from `django.utils.timezone` because:
- Django's `USE_TZ = True` setting makes all stored datetimes timezone-aware
- Python's `datetime.now()` returns a *naive* datetime (no timezone info)
- Comparing aware and naive datetimes raises `TypeError`
- `timezone.now()` always returns an aware datetime matching Django's setting

---

## 9. Student Access Control

Students can only see assignments if **both** conditions are true:
1. The assignment is `is_published=True`
2. The student is a member of the assignment's classroom (via `ClassroomMembership`)

This is enforced at the **queryset level** in `get_queryset()`, not in `has_permission()`. Why? Because filtering in `get_queryset()` returns **404** (not found) instead of **403** (forbidden). A 404 is more secure — it doesn't reveal that the assignment or classroom exists.

```python
# StudentAssignmentDetailView — the security filter:
Assignment.objects.filter(
    is_published=True,
    classroom__students=self.request.user  # student must be in the classroom
)
```

The `classroom__students` lookup works because `Classroom.students` is a ManyToMany field (via `ClassroomMembership`). Django traverses the relationship automatically with the `__` syntax.

---

## 10. Migration Explanation

### What is a migration?

A migration is a Python file that describes a database change. Django generates it automatically by reading your `models.py` and comparing it to previous migrations.

### Commands Used

**Step 1: Generate the migration file**
```bash
cd backend
python manage.py makemigrations assignments
```
- Reads `assignments/models.py`
- Compares with existing migration history (none for `assignments`)
- Creates `assignments/migrations/0001_initial.py`
- **Does NOT touch the database** — only writes a Python file

**Step 2: Apply the migration**
```bash
python manage.py migrate
```
- Reads all pending `.py` migration files
- Executes the corresponding SQL (`CREATE TABLE assignments_assignment ...`)
- Updates `django_migrations` table to track what has been applied

### What `0001_initial.py` creates

The migration creates one SQL table: `assignments_assignment` with columns:
- `id` (BigAutoField, primary key)
- `title` (VARCHAR 255, NOT NULL)
- `description` (TEXT, NOT NULL, default '')
- `instructions` (TEXT, NOT NULL, default '')
- `due_date` (DATETIME, nullable)
- `max_marks` (PositiveInteger, NOT NULL, default 100)
- `language` (VARCHAR 20, NOT NULL, default 'python')
- `difficulty` (VARCHAR 10, NOT NULL, default 'medium')
- `is_published` (BOOLEAN, NOT NULL, default False)
- `created_at` (DATETIME, NOT NULL, auto-set)
- `updated_at` (DATETIME, NOT NULL, auto-set)
- `classroom_id` (INTEGER FK → classrooms_classroom)
- `created_by_id` (INTEGER FK → accounts_user)

> **Note:** `is_past_due` and `status` are `@property` values — they are **not** stored in the database. They are computed at read time.

---

## 11. Test Results

**Test suite run:**
```
python manage.py test accounts classrooms assignments -v 2
```

**Results:**

| App | Tests | Status |
|-----|-------|--------|
| `accounts` | 40 | ✅ All pass |
| `classrooms` | 33 | ✅ All pass |
| `assignments` | 49 | ✅ All pass |
| **Total** | **122** | **✅ All pass** |

### Assignment Test Coverage

| Test Class | Tests | What is tested |
|------------|-------|----------------|
| `AssignmentModelTest` | 10 | Model fields, defaults, `is_past_due`, `status`, `__str__`, ordering |
| `TeacherAssignmentCreateTest` | 8 | POST create, auto-set classroom/creator, draft default, ownership |
| `TeacherAssignmentListTest` | 3 | GET list, draft visibility, classroom isolation |
| `TeacherAssignmentCRUDTest` | 5 | GET detail, PATCH, DELETE, 404 on other teacher's assignment |
| `StudentAssignmentListTest` | 5 | Published-only visibility, 404 on unjoined classroom |
| `StudentAssignmentDetailTest` | 3 | Full detail, draft blocked, unjoined classroom blocked |
| `AssignmentValidationTest` | 10 | Blank title, zero marks, invalid choices, past due date on create |
| `AssignmentPermissionTest` | 7 | 401 unauthenticated, 403 wrong role, 403 pending teacher |
| **Total** | **51** | *(49 unique test methods — 2 from list test share assertions)* |

---

## 12. How to Push & Create a Pull Request

> **Important:** Do NOT merge yourself. Push, create a PR, and wait for code review.

### Step 1: Push the branch

```bash
git push origin feature/assignment-management
```

### Step 2: Go to GitHub

Open your repository at `https://github.com/<your-username>/LabCraft`

### Step 3: Create the Pull Request

1. GitHub will show a banner: **"feature/assignment-management had recent pushes"** → click **"Compare & pull request"**
2. Set the base branch to **`develop`** (NOT `main`)
3. Set the compare branch to **`feature/assignment-management`**
4. Title: `feat(assignments): Module 3 — Assignment Management`
5. Description: paste the commit message or summarize the features
6. Click **"Create pull request"**

### Step 4: Wait for review

Do NOT click "Merge pull request" yourself. Wait for your reviewer to approve.

### PR Checklist

- [x] All 122 tests pass
- [x] No modifications to `accounts`, `classrooms`, or other modules
- [x] Code submission and grading NOT implemented (Module 4 scope)
- [x] Migration file committed (`assignments/migrations/0001_initial.py`)
- [x] Admin registered
- [x] Documentation written

---

*Module 3 complete. Next: Module 4 — Code Submission.*
