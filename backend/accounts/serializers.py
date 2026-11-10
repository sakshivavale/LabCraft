"""
accounts/serializers.py

Serializers convert Python objects (like User model instances) to and
from JSON — the format used to communicate with the React frontend.

Think of a serializer like a form:
  - It validates incoming data (registration form fields).
  - It controls which fields to include in outgoing responses.
  - It NEVER exposes the password field in responses (write_only=True).
"""

from rest_framework import serializers                            # DRF's serializer tools
from django.contrib.auth.password_validation import validate_password   # Django's built-in password rules
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer  # JWT login serializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed        # JWT auth error
from django.contrib.auth import get_user_model                   # Safe way to get our custom User model

User = get_user_model()   # returns accounts.User (set by AUTH_USER_MODEL in settings.py)


# =============================================================================
# 1. USER PROFILE SERIALIZER
#    Read-only view of a user — safe to send to the frontend.
#    Passwords are NEVER included here.
# =============================================================================

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Returns public, safe user information.
    Used in registration responses, profile endpoints, and admin lists.
    """

    class Meta:
        model = User
        fields = [
            'id',           # unique database ID
            'username',     # login username
            'email',        # email address
            'first_name',   # first name
            'last_name',    # last name
            'role',         # 'student' or 'teacher'
            'is_approved',  # True/False — whether teacher is approved
            'date_joined',  # when the account was created
        ]
        # All fields are read-only: this serializer is for DISPLAYING, not editing
        read_only_fields = fields


# =============================================================================
# 2. STUDENT REGISTRATION SERIALIZER
#    Handles POST /api/auth/register/student/
# =============================================================================

class StudentRegistrationSerializer(serializers.ModelSerializer):
    """
    Accepts registration data for a new student.
    Validates it and creates a Student user in the database.
    """

    # password — write_only=True means it is accepted as INPUT but
    # NEVER returned in the response (security: never echo back passwords)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],   # enforces Django's password strength rules
        style={'input_type': 'password'}, # hint for browsable API to hide the field
        help_text="Must meet Django's password strength requirements."
    )

    # password2 — confirmation field; must match 'password'
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Re-enter password for confirmation."
    )

    class Meta:
        model = User
        fields = [
            'username',    # chosen by the student
            'email',       # must be unique
            'first_name',  # optional but encouraged
            'last_name',   # optional but encouraged
            'password',
            'password2',
        ]

    def validate_email(self, value):
        """
        Extra check: make sure no other user already has this email.
        (The model also enforces unique=True, but we give a nicer message here.)
        """
        # Case-insensitive check — 'User@Test.com' and 'user@test.com' should clash
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()   # store emails in lowercase for consistency

    def validate(self, attrs):
        """
        Cross-field validation: run after individual field validation passes.
        Check that password and password2 match.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        """
        Create the Student user in the database.
        Called automatically when serializer.save() is called in the view.
        """
        validated_data.pop('password2')   # remove the confirmation field — not needed in DB

        # create_user() hashes the password before saving (NEVER store plain text)
        user = User.objects.create_user(
            role=User.Role.STUDENT,   # hard-coded: this serializer is students only
            is_approved=True,         # students are immediately active
            **validated_data          # username, email, first_name, last_name, password
        )
        return user


# =============================================================================
# 3. TEACHER REGISTRATION SERIALIZER
#    Handles POST /api/auth/register/teacher/
# =============================================================================

class TeacherRegistrationSerializer(serializers.ModelSerializer):
    """
    Accepts registration data for a new teacher.
    Teacher accounts start as is_approved=False — admin must approve them.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2']

    def validate_email(self, value):
        """Same email-uniqueness check as StudentRegistrationSerializer."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            role=User.Role.TEACHER,   # hard-coded: teacher role
            is_approved=False,        # MUST wait for admin approval before logging in
            **validated_data
        )
        return user


# =============================================================================
# 4. CUSTOM JWT TOKEN SERIALIZER
#    Handles POST /api/auth/login/
#    Extends SimpleJWT's built-in login serializer.
# =============================================================================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom login serializer that:
      1. Embeds role and username into the JWT token (decoded by frontend without an API call).
      2. Blocks unapproved teachers from logging in.
      3. Returns user profile data alongside the tokens.
    """

    @classmethod
    def get_token(cls, user):
        """
        get_token() runs when login succeeds.
        We call the parent to get a standard token, then add our own claims.

        'Claims' are key-value pairs stored INSIDE the JWT itself.
        The React frontend can read these by decoding the token (base64).
        """
        token = super().get_token(user)   # creates the JWT with standard fields (user id, expiry)

        # Add custom claims — these travel inside the JWT token
        token['role'] = user.role         # e.g. 'student' or 'teacher'
        token['username'] = user.username # so frontend knows who is logged in without an extra API call

        return token

    def validate(self, attrs):
        """
        validate() checks credentials AND our custom business rules.
        Called automatically by the view when request data comes in.
        """
        # 1. Let the parent verify username + password (raises AuthenticationFailed if wrong)
        data = super().validate(attrs)

        # 2. self.user is set by the parent after successful credential check
        user = self.user

        # 3. BLOCK unapproved teachers — they have valid credentials but
        #    aren't allowed to log in until admin approves them
        if user.is_teacher and not user.is_approved:
            raise AuthenticationFailed(
                "Your teacher account is pending admin approval. "
                "You will receive access once an administrator reviews your registration."
            )

        # 4. Add a 'user' key to the JSON response so the frontend gets user info
        #    alongside the access and refresh tokens in one response
        data['user'] = {
            'id':          user.id,
            'username':    user.username,
            'email':       user.email,
            'first_name':  user.first_name,
            'last_name':   user.last_name,
            'role':        user.role,
            'is_approved': user.is_approved,
        }

        return data   # contains: access, refresh, user


# =============================================================================
# 5. PROFILE UPDATE SERIALIZER
#    Handles PATCH /api/auth/profile/
# =============================================================================

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Allows a logged-in user to update their own first_name, last_name, and email.
    Role and approval status cannot be changed by the user themselves.
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def validate_email(self, value):
        """
        When updating email, make sure no OTHER user has this email.
        We exclude the current user from the check.
        """
        user = self.context['request'].user   # the currently logged-in user
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value.lower()
