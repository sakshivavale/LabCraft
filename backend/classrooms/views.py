"""
classrooms/views.py

API views for the Classroom Management module.

Who can do what:
  - Approved Teacher: create, edit, delete OWN classrooms; view own classroom's students.
  - Student: join a classroom using a code; view their own joined classrooms; leave a classroom.
  - Both: view classroom details (if they are a member or owner).

We import permission classes from accounts.permissions — no new User model needed.
"""

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import IntegrityError

from accounts.permissions import IsApprovedTeacher, IsStudent   # reuse from Module 1
from .models import Classroom, ClassroomMembership
from .serializers import (
    ClassroomListSerializer,
    ClassroomDetailSerializer,
    ClassroomWriteSerializer,
    JoinClassroomSerializer,
    ClassroomMembershipSerializer,
)


# =============================================================================
# 1. TEACHER: CREATE CLASSROOM + LIST OWN CLASSROOMS
#    GET  /api/classrooms/           → teacher sees their own classrooms
#    POST /api/classrooms/           → teacher creates a new classroom
# =============================================================================

class ClassroomListCreateView(generics.ListCreateAPIView):
    """
    GET  → Returns all classrooms owned by the logged-in teacher.
    POST → Creates a new classroom for the logged-in teacher.

    Only approved teachers can access this view.
    """
    permission_classes = [IsApprovedTeacher]   # from accounts.permissions

    def get_serializer_class(self):
        """
        Use the write serializer for POST (creating),
        and the list serializer for GET (listing).
        """
        if self.request.method == 'POST':
            return ClassroomWriteSerializer    # only name, description, is_active
        return ClassroomListSerializer         # compact view with teacher_name, student_count

    def get_queryset(self):
        """
        Return ONLY the classrooms that belong to the currently logged-in teacher.
        This prevents one teacher from seeing another teacher's classrooms.
        """
        return Classroom.objects.filter(teacher=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Override create() so we can:
          1. Set the teacher automatically from the logged-in user (not from request body).
          2. Return a custom response that includes the join_code prominently.

        WHY call serializer.save(teacher=request.user) here?
          'teacher' is not in ClassroomWriteSerializer's fields — the teacher
          can't claim to be someone else. We inject it ourselves from the JWT token.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Save once — pass teacher so the model receives it; join_code is generated inside model.save()
        classroom = serializer.save(teacher=request.user)

        return Response(
            {
                'message': f'Classroom "{classroom.name}" created successfully.',
                'join_code': classroom.join_code,   # show the teacher the generated code
                'classroom': ClassroomDetailSerializer(classroom).data,
            },
            status=status.HTTP_201_CREATED
        )


# =============================================================================
# 2. TEACHER: VIEW / EDIT / DELETE A SPECIFIC CLASSROOM
#    GET    /api/classrooms/<id>/    → view classroom details
#    PUT    /api/classrooms/<id>/    → full update
#    PATCH  /api/classrooms/<id>/    → partial update (e.g. rename)
#    DELETE /api/classrooms/<id>/    → delete the classroom
# =============================================================================

class ClassroomDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Allows a teacher to view, update, or delete ONE of their classrooms.

    Key safety check in get_queryset():
      Filtering by teacher=request.user means a teacher can ONLY
      access classrooms they own. Trying to edit another teacher's
      classroom will return 404 (not even revealing it exists).
    """
    permission_classes = [IsApprovedTeacher]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ClassroomWriteSerializer    # only writable fields on update
        return ClassroomDetailSerializer       # full details on GET

    def get_queryset(self):
        """
        SECURITY: Only return classrooms where teacher == logged-in user.
        A teacher cannot view, edit, or delete another teacher's classroom.
        """
        return Classroom.objects.filter(teacher=self.request.user)

    def update(self, request, *args, **kwargs):
        """Return a friendly message after updating."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        classroom = serializer.save()
        return Response({
            'message': f'Classroom "{classroom.name}" updated successfully.',
            'classroom': ClassroomDetailSerializer(classroom).data,
        })

    def destroy(self, request, *args, **kwargs):
        """Return a friendly message after deleting."""
        instance = self.get_object()
        name = instance.name
        instance.delete()   # deletes the classroom and all memberships (CASCADE)
        return Response(
            {'message': f'Classroom "{name}" has been deleted.'},
            status=status.HTTP_200_OK
        )


# =============================================================================
# 3. TEACHER: VIEW STUDENTS IN THEIR CLASSROOM
#    GET /api/classrooms/<id>/students/
# =============================================================================

class ClassroomStudentListView(generics.ListAPIView):
    """
    Returns a list of all students who have joined a specific classroom.
    Only the teacher who OWNS that classroom can view this.
    """
    permission_classes = [IsApprovedTeacher]
    serializer_class = ClassroomMembershipSerializer

    def get_queryset(self):
        """
        1. Find the classroom with pk=<id> that belongs to this teacher.
        2. Return all membership records for that classroom.
        get_object_or_404 automatically returns 404 if not found.
        """
        # 'pk' is the classroom's ID from the URL: /api/classrooms/5/students/
        classroom = get_object_or_404(
            Classroom,
            pk=self.kwargs['pk'],            # classroom ID from URL
            teacher=self.request.user        # MUST belong to this teacher
        )
        return ClassroomMembership.objects.filter(classroom=classroom)


# =============================================================================
# 4. STUDENT: JOIN A CLASSROOM
#    POST /api/classrooms/join/
# =============================================================================

class JoinClassroomView(APIView):
    """
    Student submits a join code to enter a classroom.

    Steps:
      1. Validate the join code (serializer checks the code exists and is active).
      2. Check the student hasn't already joined this classroom.
      3. Create a ClassroomMembership record.
    """
    permission_classes = [IsStudent]   # only students can join classrooms

    def post(self, request):
        serializer = JoinClassroomSerializer(
            data=request.data,
            context={'request': request}   # context lets the serializer access the request
        )
        serializer.is_valid(raise_exception=True)

        # The serializer stored the found classroom in context during validation
        classroom = serializer.context['classroom']

        # Check: has this student already joined this classroom?
        # We check BEFORE creating to give a clear error message.
        already_member = ClassroomMembership.objects.filter(
            student=request.user,
            classroom=classroom
        ).exists()   # .exists() is faster than .count() — stops as soon as one is found

        if already_member:
            return Response(
                {'error': f'You have already joined "{classroom.name}".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the membership record (the student is now in the classroom)
        try:
            membership = ClassroomMembership.objects.create(
                student=request.user,
                classroom=classroom
            )
        except IntegrityError:
            # IntegrityError is a database-level duplicate protection.
            # This is a second safety net in case of a race condition.
            return Response(
                {'error': 'You are already a member of this classroom.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                'message': f'You have successfully joined "{classroom.name}"!',
                'classroom': ClassroomDetailSerializer(classroom).data,
            },
            status=status.HTTP_201_CREATED
        )


# =============================================================================
# 5. STUDENT: VIEW THEIR JOINED CLASSROOMS
#    GET /api/classrooms/my/
# =============================================================================

class MyClassroomsView(generics.ListAPIView):
    """
    Returns all classrooms that the currently logged-in student has joined.
    """
    permission_classes = [IsStudent]
    serializer_class = ClassroomListSerializer

    def get_queryset(self):
        """
        joined_classrooms is the reverse relation we set on the ManyToManyField:
          related_name='joined_classrooms'
        So: request.user.joined_classrooms.all() → all classrooms this student is in.
        We only show active classrooms.
        """
        return self.request.user.joined_classrooms.filter(is_active=True)


# =============================================================================
# 6. STUDENT: LEAVE A CLASSROOM
#    DELETE /api/classrooms/<id>/leave/
# =============================================================================

class LeaveClassroomView(APIView):
    """
    Allows a student to leave a classroom they previously joined.
    Deletes their ClassroomMembership record.
    """
    permission_classes = [IsStudent]

    def delete(self, request, pk):
        """
        'pk' is the classroom ID from the URL.
        We look for the student's membership in that classroom.
        """
        membership = ClassroomMembership.objects.filter(
            student=request.user,
            classroom_id=pk    # classroom_id is the FK column — classroom__id
        ).first()   # returns None if not found (doesn't raise an exception)

        if not membership:
            return Response(
                {'error': 'You are not a member of this classroom.'},
                status=status.HTTP_404_NOT_FOUND
            )

        classroom_name = membership.classroom.name
        membership.delete()   # remove the membership record from the database

        return Response(
            {'message': f'You have left "{classroom_name}".'},
            status=status.HTTP_200_OK
        )


# =============================================================================
# 7. CLASSROOM DETAIL VIEW FOR STUDENTS
#    GET /api/classrooms/<id>/detail/
#    Students can view details of a classroom they are a member of.
# =============================================================================

class ClassroomDetailForStudentView(generics.RetrieveAPIView):
    """
    Allows a student to view the details of a classroom they have joined.
    Cannot see classrooms they haven't joined.
    """
    permission_classes = [IsStudent]
    serializer_class = ClassroomDetailSerializer

    def get_queryset(self):
        """
        joined_classrooms gives all classrooms this student is in.
        """
        return self.request.user.joined_classrooms.filter(is_active=True)
