from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import connection

from ..models import AppUser
from ..serializers import LoginSerializer


class IsHROrAdmin(BasePermission):
    """Allows access only to HR managers or Admins."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['hr', 'admin']
        )


from rest_framework.decorators import throttle_classes
from rest_framework.throttling import AnonRateThrottle

class LoginThrottle(AnonRateThrottle):
    rate = '5/minute'
    scope = 'login'

@api_view(['POST'])
@throttle_classes([LoginThrottle])
def login_view(request):
    """Validate credentials against AppUser table and return JWT tokens."""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email'].lower().strip()
    password = serializer.validated_data['password']
    role = serializer.validated_data['role']

    generic_error = 'Invalid email, password, or role.'

    try:
        user = AppUser.objects.get(email=email, role=role)
    except AppUser.DoesNotExist:
        return Response(
            {'error': generic_error},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.check_password(password):
        return Response(
            {'error': generic_error},
            status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)
    return Response({
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'role': user.role,
        'fullName': user.full_name,
        'phone': user.phone,
        'dob': user.dob.isoformat() if user.dob else None,
        'designation': user.designation,
        'address': user.address,
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Public health check endpoint.
    Verifies database connection status without exposing configuration details.
    """
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    return Response({
        "status": "healthy" if db_ok else "unhealthy",
        "database": {
            "connected": db_ok
        }
    }, status=status.HTTP_200_OK if db_ok else status.HTTP_500_INTERNAL_SERVER_ERROR)
