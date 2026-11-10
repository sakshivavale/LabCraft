# Module 2 — Classroom Management

> **LabCraft Backend | Django REST Framework**
> Branch: `feature/classroom-management`
> Author: LabCraft Dev Team
> Date: November 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [What Was Already There (Module 1)](#2-what-was-already-there-module-1)
3. [Module 2 — What We Built](#3-module-2--what-we-built)
4. [File-by-File Explanation](#4-file-by-file-explanation)
   - [models.py](#41-classroomsmodelspy)
   - [serializers.py](#42-classroomsserializerspy)
   - [permissions.py (from accounts)](#43-accountspermissionspy-reused)
   - [views.py](#44-classroomsviewspy)
   - [urls.py](#45-classroomsurlspy)
   - [admin.py](#46-classroomsadminpy)
   - [apps.py](#47-classroomsappspy)
   - [tests.py](#48-classroomstestspy)
5. [Database Models — ER Diagram](#5-database-models--er-diagram)
6. [API Endpoints — Full Reference](#6-api-endpoints--full-reference)
7. [How Permissions Work](#7-how-permissions-work)
8. [The Join Code System — How It Works](#8-the-join-code-system--how-it-works)
9. [Migration Explanation](#9-migration-explanation)
10. [Bugs Found and Fixed](#10-bugs-found-and-fixed)
11. [Test Results](#11-test-results)
12. [How to Push and Create a Pull Request](#12-how-to-push-and-create-a-pull-request)

---

## 1. Overview

Module 2 adds **Classroom Management** to LabCraft — a system where:

| Who | Can Do |
|-----|--------|
| **Approved Teacher** | Create, edit, delete their own classrooms; view their students |
| **Student** | Join a classroom using a 6–8 character code; view joined classrooms; leave a classroom |
| **Admin** | Full access via Django Admin panel |

**Key Design Principles:**
- Uses the **same `accounts.User` model** from Module 1 — no second user model.
- Uses **role-based permissions** (`IsApprovedTeacher`, `IsStudent`) from `accounts.permissions`.
- The join code is **auto-generated** — teachers never type it in; students use it to join.
- A student **cannot join the same classroom twice** — enforced at both API level and database level.

---

## 2. What Was Already There (Module 1)

Module 1 (`accounts` app) gave us:

```python
# accounts/models.py
class User(AbstractUser):
    role = models.CharField(choices=[('student', 'Student'), ('teacher', 'Teacher')])
    is_approved = models.BooleanField(default=False)

    @property
    def is_student(self): ...
    @property
    def is_teacher(self): ...
    @property
    def is_teacher_approved(self): ...  # True only if teacher AND approved
```

```python
# accounts/permissions.py
class IsStudent(BasePermission): ...          # only students pass
class IsTeacher(BasePermission): ...          # any teacher passes
class IsApprovedTeacher(BasePermission): ...  # only approved teachers pass
```

Module 2 **imports and reuses** these — it does NOT create another User model.

---

## 3. Module 2 — What We Built

### New Files Created / Updated:

```
backend/classrooms/
├── models.py         ← Classroom + ClassroomMembership models
├── serializers.py    ← JSON conversion for API requests/responses
├── views.py          ← API endpoint logic
├── urls.py           ← URL routing
├── admin.py          ← Django Admin panel integration
├── apps.py           ← App configuration
├── tests.py          ← 33 automated tests (all passing ✅)
└── migrations/
    └── 0001_initial.py  ← Creates DB tables
```

---

## 4. File-by-File Explanation

### 4.1 `classrooms/models.py`

This file defines the **database structure** for the classroom system.

#### Why Two Models?

We need to represent a **many-to-many relationship**:
- One classroom has many students.
- One student can join many classrooms.

We could use Django's built-in `ManyToManyField`, but we use a **custom through model** (`ClassroomMembership`) because we want to store *extra data* — specifically, **when** a student joined.

---

#### Model 1: `Classroom`

```python
class Classroom(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,     # points to accounts.User
        on_delete=models.CASCADE,     # delete classroom if teacher deleted
        related_name='classrooms',    # teacher.classrooms.all() gives all their rooms
        limit_choices_to={'role': 'teacher'},
    )
```

**WHY `settings.AUTH_USER_MODEL` instead of `User` directly?**
Using `settings.AUTH_USER_MODEL` is a string reference (`'accounts.User'`). This avoids circular import issues that happen when you import the model directly at the top of the file. Django resolves it at the right time.

**WHY `related_name='classrooms'`?**
This lets us write `teacher.classrooms.all()` to get all classrooms belonging to a teacher. Without `related_name`, Django would generate an ugly accessor name automatically.

**WHY `on_delete=CASCADE`?**
If a teacher account is deleted, all their classrooms are deleted too. This keeps the database clean — no "orphan" classrooms without owners.

---

```python
    join_code = models.CharField(
        max_length=10,
        unique=True,
        blank=True,  # teacher doesn't type this — we generate it
    )
```

**WHY `unique=True`?**
No two classrooms can share the same join code. If they did, students wouldn't know which classroom to enter.

**WHY `blank=True`?**
We set `blank=True` to tell Django's form validation that this field is not required from the user. We generate it ourselves in `save()`.

---

```python
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ClassroomMembership',    # use our custom join table
        related_name='joined_classrooms', # student.joined_classrooms.all()
    )
```

**WHY `through='ClassroomMembership'`?**
Normally a ManyToManyField creates a simple join table with just two foreign keys. We use `through=` to tell Django to use OUR custom table, which also stores `joined_at` (the date the student joined).

---

```python
    def save(self, *args, **kwargs):
        if not self.join_code:    # only generate if the code is empty (first save)
            self.join_code = self._generate_unique_code()
        super().save(*args, **kwargs)
```

**WHY override `save()`?**
We want the join code to be generated **automatically every time a classroom is created**, no matter how it's created — via the API, via Django Admin, or via the Django shell. By putting the generation logic in `save()`, we guarantee it always runs.

**WHY `if not self.join_code`?**
We only generate a code if the classroom doesn't already have one. This prevents the code from being regenerated every time the classroom is updated (e.g., if a teacher renames the classroom).

---

```python
    @staticmethod
    def _generate_unique_code():
        while True:
            code = uuid.uuid4().hex[:8].upper()   # e.g. 'A3F2D1B4'
            if not Classroom.objects.filter(join_code=code).exists():
                return code
```

**Step by step — how the join code is generated:**
1. `uuid.uuid4()` → Creates a random UUID like `3f2d1b4a-9c8e-4f7a-b6d2-...`
2. `.hex` → Removes dashes → `3f2d1b4a9c8e4f7a...`
3. `[:8]` → Takes first 8 characters → `3f2d1b4a`
4. `.upper()` → Makes uppercase → `3F2D1B4A`
5. The `while True` loop keeps trying until it finds a code that doesn't exist in the DB yet. In practice, collisions are astronomically rare (16^8 = ~4 billion possibilities).

---

#### Model 2: `ClassroomMembership`

```python
class ClassroomMembership(models.Model):
    student = models.ForeignKey(...)
    classroom = models.ForeignKey(...)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'classroom'],
                name='unique_student_classroom'
            )
        ]
```

**WHY `UniqueConstraint`?**
This is the most important constraint. It tells the database: **the combination of (student, classroom) must be unique**. This means a student CANNOT join the same classroom twice. The database itself will reject duplicate rows.

This is a "second safety net" — the API view also checks for duplicates before creating, but this database constraint is the final guarantee.

**WHY `auto_now_add=True` for `joined_at`?**
`auto_now_add=True` automatically sets the field to the current date/time when the record is first created, and never changes it again. This is exactly what we want — record when the student joined, and never change that.

---

### 4.2 `classrooms/serializers.py`

Serializers convert **Python objects ↔ JSON**. Think of them as smart forms:
- They validate data coming in (from API requests).
- They control which fields to show going out (in API responses).

#### `ClassroomListSerializer` — Compact view for listing

```python
class ClassroomListSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    student_count = serializers.IntegerField(read_only=True)
    # NOTE: No 'source' argument here — DRF raises AssertionError if
    # source == field_name (it's considered redundant and a mistake).
```

**WHY `SerializerMethodField` for `teacher_name`?**
The `teacher` field on the model is a foreign key to a User object. We don't want to return the full teacher object in a list view (too much data). We use `SerializerMethodField` with a custom `get_teacher_name()` method to return just the teacher's name.

**WHY no `source='student_count'`?**
When the field name exactly matches the source name, DRF raises `AssertionError: It is redundant to specify source=... Remove the source keyword argument.` We just write `student_count = serializers.IntegerField(read_only=True)` and DRF finds the `@property` on the model automatically.

---

#### `ClassroomDetailSerializer` — Full details for single classroom

```python
class ClassroomDetailSerializer(serializers.ModelSerializer):
    teacher = UserProfileSerializer(read_only=True)   # nested object
    students = UserProfileSerializer(many=True, read_only=True)
    student_count = serializers.IntegerField(read_only=True)
```

**WHY `UserProfileSerializer(read_only=True)`?**
Nesting a serializer inside another gives us the full teacher/student profile data in the response. `read_only=True` means this data is only for displaying — the user cannot change the teacher by sending data in this format.

**WHY import from `accounts.serializers`?**
We reuse `UserProfileSerializer` from Module 1 instead of re-defining what a "user" looks like. This is the correct approach — Module 2 depends on Module 1, not the other way around.

---

#### `ClassroomWriteSerializer` — Create/update serializer

```python
class ClassroomWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = ['name', 'description', 'is_active']
        # NOTE: 'teacher' and 'join_code' are intentionally NOT here.
        # teacher → set by the view from the JWT token (request.user)
        # join_code → auto-generated in model.save()
```

**WHY are `teacher` and `join_code` not in the fields?**
Security. If we included `teacher` in the writable fields, a malicious teacher could set themselves as the teacher of someone else's classroom. By excluding these fields, we ensure they can only be set by the server — never by the user.

---

#### `JoinClassroomSerializer` — Accepts a join code from a student

```python
class JoinClassroomSerializer(serializers.Serializer):
    join_code = serializers.CharField(max_length=10, min_length=6)

    def validate_join_code(self, value):
        code = value.strip().upper()   # normalize — 'abc123ef' → 'ABC123EF'
        try:
            classroom = Classroom.objects.get(join_code=code)
        except Classroom.DoesNotExist:
            raise serializers.ValidationError("No classroom found...")
        if not classroom.is_active:
            raise serializers.ValidationError("This classroom is not active...")
        self.context['classroom'] = classroom   # store for the view to use
        return code
```

**WHY `serializers.Serializer` instead of `ModelSerializer`?**
We're not creating a Classroom — we're looking one up by its join code, then creating a `ClassroomMembership`. A plain `Serializer` is cleaner here because we don't have a model to base it on.

**WHY `value.strip().upper()`?**
Case normalization — if a student types `abc123EF` or `  ABC123EF  `, we convert it to `ABC123EF` before searching. This makes the system user-friendly.

**WHY store classroom in `self.context['classroom']`?**
After validation finds the classroom, the view needs to use it without hitting the database again. We store it in the serializer's context dictionary so the view can retrieve it with `serializer.context['classroom']`.

---

### 4.3 `accounts/permissions.py` (Reused)

Module 2 imports permissions directly from Module 1:

```python
from accounts.permissions import IsApprovedTeacher, IsStudent
```

| Permission Class | Who Passes |
|-----------------|-----------|
| `IsApprovedTeacher` | Logged-in users with `role='teacher'` AND `is_approved=True` |
| `IsStudent` | Logged-in users with `role='student'` |

**WHY NOT create new permission classes?**
Module 1 already defined these precisely. Creating duplicates would lead to inconsistency — if the approval logic changed in Module 1, Module 2 wouldn't get the update automatically.

---

### 4.4 `classrooms/views.py`

Views receive HTTP requests and return JSON responses.

#### View 1: `ClassroomListCreateView`

```python
class ClassroomListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsApprovedTeacher]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ClassroomWriteSerializer    # for creating
        return ClassroomListSerializer         # for listing

    def get_queryset(self):
        return Classroom.objects.filter(teacher=self.request.user)
        # WHY filter by teacher? A teacher should ONLY see THEIR OWN classrooms.
        # Without this filter, every teacher could see every classroom.
```

```python
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        classroom = serializer.save(teacher=request.user)
        # WHY serializer.save(teacher=request.user)?
        # 'teacher' is not in ClassroomWriteSerializer's fields.
        # We inject it here from the JWT token (request.user).
        # This is called ONCE — no perform_create() override,
        # which would cause a double-save bug.
        return Response({
            'message': f'Classroom "{classroom.name}" created successfully.',
            'join_code': classroom.join_code,
            'classroom': ClassroomDetailSerializer(classroom).data,
        }, status=status.HTTP_201_CREATED)
```

**IMPORTANT: Why no `perform_create()`?**
`generics.ListCreateAPIView` has a default `create()` method that calls `perform_create()`. If you override `create()` AND also define `perform_create()`, the teacher assignment happens TWICE — once in `create()` and once when `perform_create()` is called internally. This causes a bug. We override ONLY `create()` and do the save ourselves.

---

#### View 2: `ClassroomDetailView`

```python
class ClassroomDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsApprovedTeacher]

    def get_queryset(self):
        return Classroom.objects.filter(teacher=self.request.user)
        # SECURITY: A teacher can only see/edit/delete classrooms where
        # THEY are the teacher. Trying to access another teacher's
        # classroom returns 404 — not even revealing it exists.
```

**WHY 404 instead of 403?**
Returning 403 (Forbidden) would reveal that the classroom EXISTS but the user doesn't have access. Returning 404 (Not Found) is more secure — the other teacher's classroom is as if it doesn't exist for you.

---

#### View 3: `JoinClassroomView`

```python
class JoinClassroomView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = JoinClassroomSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        classroom = serializer.context['classroom']

        # First safety net: check before creating
        already_member = ClassroomMembership.objects.filter(
            student=request.user,
            classroom=classroom
        ).exists()

        if already_member:
            return Response(
                {'error': f'You have already joined "{classroom.name}".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create membership
        try:
            membership = ClassroomMembership.objects.create(
                student=request.user,
                classroom=classroom
            )
        except IntegrityError:
            # Second safety net: database-level unique constraint catches
            # race conditions (two simultaneous requests from same student)
            return Response(
                {'error': 'You are already a member of this classroom.'},
                status=status.HTTP_400_BAD_REQUEST
            )
```

**WHY two checks for duplicate membership?**
The `.exists()` check is fast and gives a friendly error message. The `IntegrityError` catch handles the rare case where two requests arrive at the same time (race condition) — both pass the `.exists()` check, but only one can succeed at the database level.

---

#### View 4: `MyClassroomsView`

```python
class MyClassroomsView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = ClassroomListSerializer

    def get_queryset(self):
        return self.request.user.joined_classrooms.filter(is_active=True)
        # 'joined_classrooms' is the related_name on the ManyToManyField:
        # students = ManyToManyField(..., related_name='joined_classrooms')
        # So: request.user.joined_classrooms.all() → all classrooms this student joined
        # We filter to is_active=True → students only see live classrooms
```

---

### 4.5 `classrooms/urls.py`

```python
urlpatterns = [
    # TEACHER endpoints
    path('', ClassroomListCreateView.as_view(), name='classroom-list-create'),
    path('<int:pk>/', ClassroomDetailView.as_view(), name='classroom-detail'),
    path('<int:pk>/students/', ClassroomStudentListView.as_view(), name='classroom-students'),

    # STUDENT endpoints
    path('join/', JoinClassroomView.as_view(), name='classroom-join'),
    path('my/', MyClassroomsView.as_view(), name='my-classrooms'),
    path('<int:pk>/detail/', ClassroomDetailForStudentView.as_view(), name='classroom-detail-student'),
    path('<int:pk>/leave/', LeaveClassroomView.as_view(), name='classroom-leave'),
]
```

These are mounted under `/api/classrooms/` in `config/urls.py`.

**WHY separate `/detail/` and `/leave/` paths?**
The `<int:pk>/` path is owned by the teacher (for edit/delete). Students use `<int:pk>/detail/` and `<int:pk>/leave/` to avoid permission conflicts.

---

### 4.6 `classrooms/admin.py`

```python
class ClassroomMembershipInline(admin.TabularInline):
    # Shows student memberships as a table INSIDE the Classroom admin page
    model = ClassroomMembership
    extra = 0            # don't show empty rows
    readonly_fields = ['student', 'joined_at']
    can_delete = True    # admin can remove a student

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display  = ['name', 'teacher', 'join_code', 'student_count', 'is_active', 'created_at']
    readonly_fields = ['join_code', 'created_at', 'updated_at']
    # join_code is auto-generated — admin should NOT be able to change it
    inlines = [ClassroomMembershipInline]
```

**WHY `readonly_fields = ['join_code', ...]`?**
The join code is generated by the system. Allowing admin to change it would break links students have — they'd try to join with the old code and get an error. Making it read-only prevents accidental changes.

---

### 4.7 `classrooms/apps.py`

```python
class ClassroomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'classrooms'
    verbose_name = 'Classroom Management'
```

Simple metadata. `verbose_name` appears in Django Admin's left sidebar.

---

### 4.8 `classrooms/tests.py`

We have **33 tests** across 6 test classes:

| Test Class | Tests | What It Checks |
|-----------|-------|----------------|
| `ClassroomModelTest` | 8 | Model fields, join code generation, uniqueness, `__str__` |
| `TeacherClassroomCRUDTest` | 7 | Create, list, update, delete; ownership security |
| `StudentJoinClassroomTest` | 6 | Join with code, duplicate prevention, inactive rooms, case-insensitive codes |
| `StudentClassroomViewTest` | 3 | View joined classrooms, cannot see non-joined |
| `StudentLeaveClassroomTest` | 2 | Leave classroom, error if not a member |
| `TeacherStudentListTest` | 2 | Teacher sees their students; cannot see another's |
| `PermissionTest` | 5 | 401/403 for wrong roles and unauthenticated access |

**Helper functions at the top:**
```python
def make_student(username, ...):
    return User.objects.create_user(role=User.Role.STUDENT, is_approved=True, ...)

def make_teacher(username, ..., approved=True):
    return User.objects.create_user(role=User.Role.TEACHER, is_approved=approved, ...)
```

**WHY helper functions?**
Every test class needs users. Without helpers, we'd repeat the same 5-line `create_user(...)` block dozens of times. Helpers make tests shorter and easier to read.

---

## 5. Database Models — ER Diagram

```
┌─────────────────────────────────┐
│          accounts_user           │
│─────────────────────────────────│
│ id (PK)                         │
│ username                        │
│ email (unique)                  │
│ password (hashed)               │
│ role ('student' | 'teacher')    │
│ is_approved (bool)              │
│ first_name, last_name           │
│ date_joined                     │
└─────────────┬───────────────────┘
              │                    
       teacher│ (FK, CASCADE)      
              │                    
┌─────────────▼───────────────────┐
│         classrooms_classroom     │
│─────────────────────────────────│
│ id (PK)                         │
│ name                            │
│ description                     │
│ join_code (unique, 8 chars)     │
│ is_active (bool, default=True)  │
│ created_at (auto)               │
│ updated_at (auto)               │
└─────────────┬───────────────────┘
              │                    
    classroom │ (FK, CASCADE)      
              │                    
┌─────────────▼───────────────────────┐
│    classrooms_classroommembership    │
│─────────────────────────────────────│
│ id (PK)                             │
│ student_id (FK → accounts_user)     │
│ classroom_id (FK → classroom)       │
│ joined_at (auto)                    │
│ UNIQUE(student_id, classroom_id)    │
└─────────────────────────────────────┘
```

---

## 6. API Endpoints — Full Reference

> All endpoints are prefixed with `/api/classrooms/`
> Authentication: `Authorization: Bearer <access_token>`

### Teacher Endpoints

| Method | URL | Permission | Description |
|--------|-----|-----------|-------------|
| `GET` | `/api/classrooms/` | Approved Teacher | List your classrooms |
| `POST` | `/api/classrooms/` | Approved Teacher | Create a new classroom |
| `GET` | `/api/classrooms/<id>/` | Approved Teacher (owner) | View classroom details |
| `PATCH` | `/api/classrooms/<id>/` | Approved Teacher (owner) | Update name/description |
| `PUT` | `/api/classrooms/<id>/` | Approved Teacher (owner) | Full replace |
| `DELETE` | `/api/classrooms/<id>/` | Approved Teacher (owner) | Delete classroom |
| `GET` | `/api/classrooms/<id>/students/` | Approved Teacher (owner) | List students in classroom |

### Student Endpoints

| Method | URL | Permission | Description |
|--------|-----|-----------|-------------|
| `POST` | `/api/classrooms/join/` | Student | Join classroom by code |
| `GET` | `/api/classrooms/my/` | Student | View your joined classrooms |
| `GET` | `/api/classrooms/<id>/detail/` | Student (member) | View classroom details |
| `DELETE` | `/api/classrooms/<id>/leave/` | Student (member) | Leave a classroom |

---

### Example: Create a Classroom

**Request:**
```http
POST /api/classrooms/
Authorization: Bearer <teacher_access_token>
Content-Type: application/json

{
    "name": "Python Lab - Sem 3",
    "description": "Practical Python programming lab for semester 3 students."
}
```

**Response (201 Created):**
```json
{
    "message": "Classroom \"Python Lab - Sem 3\" created successfully.",
    "join_code": "A3F2D1B4",
    "classroom": {
        "id": 1,
        "name": "Python Lab - Sem 3",
        "description": "Practical Python programming lab...",
        "join_code": "A3F2D1B4",
        "teacher": {
            "id": 5,
            "username": "prof_smith",
            "email": "smith@labcraft.edu",
            "first_name": "John",
            "last_name": "Smith",
            "role": "teacher",
            "is_approved": true,
            "date_joined": "2026-11-01T10:00:00Z"
        },
        "students": [],
        "student_count": 0,
        "is_active": true,
        "created_at": "2026-11-10T09:00:00Z",
        "updated_at": "2026-11-10T09:00:00Z"
    }
}
```

---

### Example: Student Joins Classroom

**Request:**
```http
POST /api/classrooms/join/
Authorization: Bearer <student_access_token>
Content-Type: application/json

{
    "join_code": "a3f2d1b4"
}
```

> Note: lowercase input is accepted — the system normalizes to uppercase.

**Response (201 Created):**
```json
{
    "message": "You have successfully joined \"Python Lab - Sem 3\"!",
    "classroom": {
        "id": 1,
        "name": "Python Lab - Sem 3",
        ...
    }
}
```

**If student tries to join again (400 Bad Request):**
```json
{
    "error": "You have already joined \"Python Lab - Sem 3\"."
}
```

---

### Example: Wrong Role (403 Forbidden)

```http
POST /api/classrooms/
Authorization: Bearer <student_access_token>

→ 403 Forbidden
{
    "detail": "Access restricted to approved teachers only. Your account may be pending approval."
}
```

---

## 7. How Permissions Work

```
HTTP Request Arrives
        │
        ▼
┌───────────────────┐
│ JWT Token parsed  │ ← reads Authorization: Bearer <token>
│ request.user set  │ ← user object loaded from DB
└───────┬───────────┘
        │
        ▼
┌───────────────────────┐
│ permission_classes    │ ← each class's has_permission() is called
│ checked in order      │
└───────┬───────────────┘
        │
  All pass?
   YES → View runs
   NO  → 401 (not logged in) or 403 (wrong role)
```

**Example for `ClassroomListCreateView`:**
```python
permission_classes = [IsApprovedTeacher]
```

`IsApprovedTeacher.has_permission()` checks:
1. Is `request.user` a real user (not anonymous)?
2. Is the user authenticated (has valid JWT)?
3. Is `user.role == 'teacher'`?
4. Is `user.is_approved == True`?

All four must be True. If any fails, the request is rejected.

---

## 8. The Join Code System — How It Works

```
Teacher creates classroom
         │
         ▼
Classroom.save() called
         │
         ▼
join_code is empty?
  YES → _generate_unique_code()
         │
         ▼
  uuid.uuid4().hex[:8].upper()
  → 'A3F2D1B4'
         │
  Is this code already in DB?
  YES → try again
  NO  → use this code
         │
         ▼
Classroom saved with join_code='A3F2D1B4'
         │
         ▼
Teacher shares code with students
         │
         ▼
Student POSTs { "join_code": "A3F2D1B4" }
         │
         ▼
JoinClassroomSerializer.validate_join_code()
  - Strips whitespace, converts to uppercase
  - Looks up classroom in DB
  - Checks classroom.is_active == True
  - Stores classroom in context
         │
         ▼
JoinClassroomView.post()
  - Checks student hasn't already joined (exists() check)
  - Creates ClassroomMembership record
  - DB UniqueConstraint catches any race condition
         │
         ▼
Student is now in the classroom ✅
```

---

## 9. Migration Explanation

### What is a migration?

A migration is a Python file that tells Django how to change the database schema (create tables, add columns, etc.). Django tracks which migrations have been run and applies only new ones.

### The initial migration: `0001_initial.py`

This was created by running:
```bash
python manage.py makemigrations classrooms
```

**What this command does:**
- Django inspects the models in `classrooms/models.py`
- It compares them to what the database currently has
- It generates a Python file describing the changes (create table, add column, etc.)
- It does NOT touch the database yet — it only creates the Python file

### Applying the migration:
```bash
python manage.py migrate
```

**What this command does:**
- Django reads all unapplied migration files
- It runs them in order against the database
- It records which migrations have been applied in the `django_migrations` table

### What `0001_initial.py` creates:

```python
# Creates classrooms_classroom table with all fields
migrations.CreateModel(name='Classroom', fields=[...])

# Creates classrooms_classroommembership table
migrations.CreateModel(name='ClassroomMembership', fields=[...])

# Adds the ManyToMany relationship
migrations.AddField(model_name='classroom', name='students', ...)
migrations.AddField(model_name='classroom', name='teacher', ...)

# Adds the unique constraint (student, classroom)
migrations.AddConstraint(...)
```

### How to check migration status:
```bash
python manage.py showmigrations classrooms
```

Output:
```
classrooms
 [X] 0001_initial
```

`[X]` means applied. `[ ]` means pending.

### When to run migrations:
- After any change to `models.py` (add field, change field, etc.)
- Run `makemigrations` first (creates the file), then `migrate` (applies it)
- **Never delete migration files** — they're the history of your database schema

---

## 10. Bugs Found and Fixed

Two bugs were found and fixed during testing:

### Bug 1: Redundant `source` in serializers

**Location:** `classrooms/serializers.py` — `ClassroomListSerializer` and `ClassroomDetailSerializer`

**Before (broken):**
```python
student_count = serializers.IntegerField(
    source='student_count',   # ← BUG: source == field name
    read_only=True
)
```

**Error:**
```
AssertionError: It is redundant to specify `source='student_count'`
on field 'IntegerField' in serializer 'ClassroomListSerializer',
because it is the same as the field name. Remove the `source` keyword argument.
```

**After (fixed):**
```python
student_count = serializers.IntegerField(read_only=True)
# DRF automatically maps this to the @property 'student_count' on the model.
```

**Why this happened:** DRF performs a strict check: if `source == field_name`, it means the developer accidentally specified something redundant. DRF raises an `AssertionError` to alert you to remove it.

---

### Bug 2: Double save in `ClassroomListCreateView`

**Location:** `classrooms/views.py` — `ClassroomListCreateView`

**Before (broken):**
```python
def perform_create(self, serializer):
    serializer.save(teacher=self.request.user)   # Save #1

def create(self, request, *args, **kwargs):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    classroom = serializer.save(teacher=request.user)  # Save #2 → DOUBLE SAVE
    return Response(...)
```

**Problem:** DRF's default `ListCreateAPIView.create()` calls `perform_create()`. When we also override `create()` and call `serializer.save()` there, the save happens TWICE. The first save creates the classroom; the second save tries to create it again, causing errors.

**After (fixed):**
```python
# Removed perform_create() entirely.
def create(self, request, *args, **kwargs):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    classroom = serializer.save(teacher=request.user)   # Save ONCE
    return Response(...)
```

**Rule:** If you override `create()` and call `serializer.save()` yourself, do NOT also define `perform_create()`. They both cause a save.

---

## 11. Test Results

```
Ran 73 tests in ~95 seconds

OK  ← all tests passed

Accounts module:  40/40 ✅
Classrooms module: 33/33 ✅
```

### Classrooms Test Breakdown

| # | Test | Verifies |
|---|------|---------|
| 1 | `test_classroom_created_with_correct_fields` | Model defaults |
| 2 | `test_join_code_auto_generated_on_save` | Auto code generation |
| 3 | `test_join_code_is_unique_across_classrooms` | No duplicate codes |
| 4 | `test_join_code_not_regenerated_on_update` | Code stability on rename |
| 5 | `test_student_count_property` | Correct count |
| 6 | `test_classroom_membership_uniqueness_constraint` | DB-level duplicate block |
| 7 | `test_str_method` | Display name |
| 8 | `test_membership_str_method` | Membership display name |
| 9 | `test_teacher_can_create_classroom` | POST returns 201 with join_code |
| 10 | `test_created_classroom_belongs_to_teacher` | Teacher correctly assigned |
| 11 | `test_teacher_lists_only_own_classrooms` | Ownership isolation |
| 12 | `test_teacher_can_update_classroom` | PATCH works |
| 13 | `test_teacher_cannot_update_another_teachers_classroom` | 404 security |
| 14 | `test_teacher_can_delete_classroom` | DELETE works |
| 15 | `test_blank_name_returns_400` | Validation |
| 16 | `test_student_can_join_with_valid_code` | Join flow |
| 17 | `test_student_cannot_join_twice` | Duplicate prevention |
| 18 | `test_invalid_join_code_returns_400` | Bad code rejected |
| 19 | `test_cannot_join_inactive_classroom` | Inactive room rejected |
| 20 | `test_teacher_cannot_join_classroom` | Role enforcement |
| 21 | `test_join_code_case_insensitive` | Lowercase input accepted |
| 22 | `test_student_sees_only_joined_classrooms` | List isolation |
| 23 | `test_student_can_view_joined_classroom_detail` | Detail view |
| 24 | `test_student_cannot_view_non_joined_classroom_detail` | Privacy |
| 25 | `test_student_can_leave_classroom` | Leave works |
| 26 | `test_student_cannot_leave_classroom_they_didnt_join` | Error on bad leave |
| 27 | `test_teacher_can_see_students_in_own_classroom` | Student list |
| 28 | `test_teacher_cannot_see_students_in_another_classroom` | 404 security |
| 29 | `test_unauthenticated_user_cannot_access_classrooms` | 401 |
| 30 | `test_student_cannot_create_classroom` | 403 |
| 31 | `test_pending_teacher_cannot_create_classroom` | 403 |
| 32 | `test_student_cannot_list_teacher_classrooms` | 403 |
| 33 | `test_my_classrooms_requires_student_role` | 403 |

---

## 12. How to Push and Create a Pull Request

### Step 1 — Push your branch to GitHub

```bash
git push origin feature/classroom-management
```

This pushes the `feature/classroom-management` branch (with all your commits) to GitHub.

### Step 2 — Create a Pull Request on GitHub

1. Go to your repository on **GitHub**
2. You'll see a yellow banner: *"feature/classroom-management had recent pushes"* → click **Compare & pull request**
3. Set:
   - **Base branch:** `develop` ← where the code should be merged INTO
   - **Compare branch:** `feature/classroom-management` ← your work
4. Title: `feat(classrooms): implement Module 2 — Classroom Management`
5. Description: Paste this summary:

```markdown
## Summary
Implements Module 2 — Classroom Management for LabCraft.

## Features Added
- Approved teachers can create, edit, and delete classrooms
- Unique 8-character join code auto-generated per classroom
- Students can join classrooms using the join code
- Duplicate join prevention (API + database level)
- Teachers can view their classroom's student list
- Students can view their joined classrooms and leave them
- Full role-based permissions (IsApprovedTeacher, IsStudent)
- Input validation on all endpoints
- Django Admin integration with inline student list

## Tests
- 33 tests added, all passing ✅
- Zero regressions in accounts module (40/40 ✅)

## Changes
- `classrooms/models.py` — Classroom + ClassroomMembership models
- `classrooms/serializers.py` — 5 serializers
- `classrooms/views.py` — 7 API views
- `classrooms/urls.py` — 7 URL patterns
- `classrooms/admin.py` — Admin with inline memberships
- `classrooms/tests.py` — 33 tests
- `docs/module2-classroom-management.md` — This documentation

## Bugs Fixed
- Removed redundant `source='student_count'` in serializers (DRF AssertionError)
- Fixed double-save bug by removing duplicate `perform_create()` override
```

6. Click **Create pull request**

### Step 3 — Do NOT merge yet

The PR should be reviewed and tested before merging into `develop`. Leave it open and notify the reviewer.

---

*Document created as part of LabCraft Module 2 — November 2026*

