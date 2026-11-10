"""
assignments/views.py

API views for the Assignment Management module.

Who can do what:
  - Approved Teacher: create, edit, delete OWN assignments inside their classrooms.
                      View all assignments (draft + published) in their classrooms.
  - Student: view PUBLISHED assignments from classrooms they have joined.
             Cannot see drafts. Cannot see assignments from unjoined classrooms.

We import permission classes from accounts.permissions — no new User model needed.
"""

from rest_framework import generics, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from accounts.permissions import IsApprovedTeacher, IsStudent   # reuse from Module 1
from classrooms.models import Classroom, ClassroomMembership    # reuse from Module 2
from .models import Assignment
from .serializers import (
    AssignmentListSerializer,
    AssignmentDetailSerializer,
    AssignmentWriteSerializer,
)


# =============================================================================
# 1. TEACHER: LIST + CREATE ASSIGNMENTS IN A CLASSROOM
#    GET  /api/assignments/classroom/<classroom_id>/   → list all assignments
#    POST /api/assignments/classroom/<classroom_id>/   → create new assignment
# =============================================================================

class TeacherAssignmentListCreateView(generics.ListCreateAPIView):
    """
    GET  → Returns all assignments (draft + published) in a classroom owned by the teacher.
    POST → Creates a new assignment in that classroom.

    Only approved teachers can access this view.
    The <classroom_id> in the URL tells us WHICH classroom to work with.
    """
    permission_classes = [IsApprovedTeacher]   # from accounts.permissions

    def get_serializer_class(self):
        """
        Use the write serializer for POST (creating/input),
        and the list serializer for GET (displaying).
        WHY two serializers? The write one accepts teacher input fields.
        The list one returns compact, computed output fields (status, is_past_due).
        """
        if self.request.method == 'POST':
            return AssignmentWriteSerializer    # only writable fields
        return AssignmentListSerializer         # compact list with computed fields

    def get_queryset(self):
        """
        SECURITY: Return only assignments that belong to a classroom
        OWNED by the currently logged-in teacher.

        How it works:
          - classroom_id comes from the URL: /api/assignments/classroom/5/
          - We filter: classroom__id=classroom_id AND classroom__teacher=request.user
          - If the classroom doesn't exist OR belongs to another teacher → empty queryset → 404
        """
        classroom_id = self.kwargs['classroom_id']   # from URL pattern
        return Assignment.objects.filter(
            classroom__id=classroom_id,
            classroom__teacher=self.request.user     # teacher can only see their own classrooms
        )

    def create(self, request, *args, **kwargs):
        """
        Override create() to:
          1. Verify the classroom exists AND belongs to this teacher.
          2. Auto-set classroom and created_by from the URL/JWT (not from request body).
          3. Return a friendly response with the full assignment details.

        WHY call serializer.save(classroom=..., created_by=...) here?
          'classroom' and 'created_by' are NOT in AssignmentWriteSerializer's fields.
          A teacher can't forge these values. We inject them ourselves from
          the URL and the JWT token (request.user).
        """
        classroom_id = self.kwargs['classroom_id']

        # get_object_or_404: returns the classroom OR raises 404 if not found/not owned.
        # This is both a lookup AND a security check in one line.
        classroom = get_object_or_404(
            Classroom,
            id=classroom_id,
            teacher=request.user    # MUST be this teacher's classroom
        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save ONCE — inject classroom and created_by here (not from user input)
        # WHY only save once? If we also had perform_create() calling save(),
        # the assignment would be saved twice → double-save bug.
        assignment = serializer.save(
            classroom=classroom,         # from URL
            created_by=request.user      # from JWT token (the logged-in teacher)
        )

        return Response(
            {
                'message': f'Assignment "{assignment.title}" created successfully.',
                'assignment': AssignmentDetailSerializer(assignment).data,
            },
            status=status.HTTP_201_CREATED
        )


# =============================================================================
# 2. TEACHER: VIEW / EDIT / DELETE A SPECIFIC ASSIGNMENT
#    GET    /api/assignments/<id>/   → view full assignment details
#    PATCH  /api/assignments/<id>/   → partial update (e.g. change due date)
#    DELETE /api/assignments/<id>/   → delete the assignment
# =============================================================================

class TeacherAssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Allows a teacher to view, update, or delete ONE of their assignments.

    Key safety check in get_queryset():
      Filtering by created_by=request.user means a teacher can ONLY
      access assignments they created. Trying to edit another teacher's
      assignment returns 404 (doesn't even reveal it exists).
    """
    permission_classes = [IsApprovedTeacher]

    def get_serializer_class(self):
        """
        Use write serializer for PATCH/PUT, detail serializer for GET.
        """
        if self.request.method in ('PUT', 'PATCH'):
            return AssignmentWriteSerializer
        return AssignmentDetailSerializer

    def get_queryset(self):
        """
        SECURITY: Only return assignments created by the logged-in teacher.
        A teacher cannot view, edit, or delete another teacher's assignment.
        """
        return Assignment.objects.filter(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        Override update() to return a friendly message after updating.
        partial=True means PATCH (only the sent fields are updated).
        partial=False means PUT (all fields must be provided).
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()   # gets the assignment from get_queryset(), raises 404 if not found
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()   # save returns the updated Assignment instance
        return Response({
            'message': f'Assignment "{assignment.title}" updated successfully.',
            'assignment': AssignmentDetailSerializer(assignment).data,
        })

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy() to return a friendly 200 message instead of empty 204.
        WHY 200 instead of 204? 204 means "no content" (empty body).
        Returning a message helps the frontend display a confirmation.
        """
        instance = self.get_object()
        title = instance.title
        instance.delete()   # deletes the assignment from the database
        return Response(
            {'message': f'Assignment "{title}" has been deleted.'},
            status=status.HTTP_200_OK
        )


# =============================================================================
# 3. STUDENT: VIEW PUBLISHED ASSIGNMENTS IN A JOINED CLASSROOM
#    GET /api/assignments/classroom/<classroom_id>/student/
# =============================================================================

class StudentAssignmentListView(generics.ListAPIView):
    """
    Returns a list of PUBLISHED assignments in a specific classroom,
    but ONLY if the student has joined that classroom.

    Key rules:
      - If student hasn't joined → 404 (don't reveal the classroom exists)
      - Draft assignments (is_published=False) are NEVER shown to students
    """
    permission_classes = [IsStudent]
    serializer_class = AssignmentListSerializer

    def get_queryset(self):
        """
        1. Get the classroom_id from the URL.
        2. Verify this student is a member of that classroom.
        3. Return only PUBLISHED assignments from that classroom.
        """
        classroom_id = self.kwargs['classroom_id']

        # Check if the student is a member of this classroom.
        # get_object_or_404 returns 404 if the student hasn't joined.
        # WHY 404 instead of 403?
        #   403 (Forbidden) says "I know this exists, but you can't access it."
        #   404 (Not Found) says "No such resource for you."
        #   We use 404 to avoid revealing that a classroom exists to non-members.
        membership = get_object_or_404(
            ClassroomMembership,
            student=self.request.user,
            classroom__id=classroom_id
        )

        # Return only published assignments — students cannot see drafts
        return Assignment.objects.filter(
            classroom=membership.classroom,
            is_published=True               # ONLY published assignments visible to students
        )


# =============================================================================
# 4. STUDENT: VIEW A SPECIFIC PUBLISHED ASSIGNMENT
#    GET /api/assignments/<id>/student/
# =============================================================================

class StudentAssignmentDetailView(generics.RetrieveAPIView):
    """
    Allows a student to view the full details of ONE published assignment,
    but ONLY if they are a member of the classroom that assignment belongs to.

    get_queryset() does the security check:
      - is_published=True            → only published assignments
      - classroom__students=user     → student must be in that classroom
        (classroom__students uses the M2M 'students' relation on Classroom)
    """
    permission_classes = [IsStudent]
    serializer_class = AssignmentDetailSerializer

    def get_queryset(self):
        """
        SECURITY: Return only published assignments from classrooms
        where the requesting student is a member.

        How 'classroom__students=request.user' works:
          Classroom has a ManyToMany 'students' field (via ClassroomMembership).
          Django lets us filter across this relation with double underscore:
          Assignment → classroom → students → must include this user.
        """
        return Assignment.objects.filter(
            is_published=True,                          # students see only published
            classroom__students=self.request.user       # student must be a member
        )
