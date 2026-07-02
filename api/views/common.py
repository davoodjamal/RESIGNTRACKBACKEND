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


@api_view(['POST'])
def login_view(request):
    """Validate credentials against AppUser table and return JWT tokens."""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email'].lower().strip()
    password = serializer.validated_data['password']
    role = serializer.validated_data['role']

    try:
        user = AppUser.objects.get(email=email, role=role)
    except AppUser.DoesNotExist:
        return Response(
            {'error': f'No {role} account found for this email.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.check_password(password):
        return Response(
            {'error': 'Invalid password.'},
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
    Verifies database connection, lists APIs, and outputs environment/diagnostic details.
    """
    db_ok = True
    db_error = None
    try:
        connection.ensure_connection()
    except Exception as e:
        db_ok = False
        db_error = str(e)

    from django.conf import settings
    db_config = settings.DATABASES.get('default', {})
    db_host = db_config.get('HOST', '')
    db_name = db_config.get('NAME', '')
    
    api_endpoints = [
        {"path": "/api/health/", "method": "GET", "description": "Health check endpoint"},
        {"path": "/api/login/", "method": "POST", "description": "Validate credentials & get JWT token"},
        {"path": "/api/users/", "method": "GET/POST", "description": "List or create users"},
        {"path": "/api/users/<pk>/", "method": "GET/PUT/PATCH/DELETE", "description": "Manage user details"},
        {"path": "/api/resignations/", "method": "GET/POST", "description": "List or submit resignations"},
        {"path": "/api/resignations/<pk>/", "method": "PATCH", "description": "Update resignation status"},
        {"path": "/api/resignations/<pk>/withdraw/", "method": "PATCH", "description": "Withdraw resignation"},
        {"path": "/api/settings/", "method": "GET/PUT", "description": "Read or update system settings"},
        {"path": "/api/audit-logs/", "method": "GET/POST", "description": "List or create audit logs"},
    ]

    return Response({
        "status": "healthy" if db_ok else "unhealthy",
        "database": {
            "connected": db_ok,
            "host": db_host,
            "name": db_name,
            "error": db_error
        },
        "endpoints": api_endpoints,
        "environment": {
            "debug": settings.DEBUG,
            "timezone": settings.TIME_ZONE,
        }
    }, status=status.HTTP_200_OK if db_ok else status.HTTP_500_INTERNAL_SERVER_ERROR)
