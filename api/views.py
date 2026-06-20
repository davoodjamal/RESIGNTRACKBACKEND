from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AppUser, Resignation, SystemSettings, AuditLog
from .serializers import (
    AppUserSerializer,
    LoginSerializer,
    ResignationSerializer,
    ResignationStatusSerializer,
    SystemSettingsSerializer,
    AuditLogSerializer,
)


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
        'email': user.email,
        'username': user.username,
        'role': user.role,
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    })


class UserListView(generics.ListCreateAPIView):
    """GET /api/users/ — list all users. POST — create new user (restricted to HR / Admin)."""
    queryset = AppUser.objects.all()
    serializer_class = AppUserSerializer
    permission_classes = [IsHROrAdmin]

    def perform_create(self, serializer):
        user = serializer.save()
        user.set_password(user.password)
        user.save()


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE /api/users/<pk>/ — manage user details (restricted to HR / Admin)."""
    queryset = AppUser.objects.all()
    serializer_class = AppUserSerializer
    permission_classes = [IsHROrAdmin]

    def perform_update(self, serializer):
        user = serializer.save()
        if 'password' in serializer.validated_data:
            user.set_password(serializer.validated_data['password'])
            user.save()


class ResignationListCreateView(generics.ListCreateAPIView):
    """GET /api/resignations/ — list all.  POST — create new."""
    queryset = Resignation.objects.all().order_by('-created_at')
    serializer_class = ResignationSerializer
    permission_classes = [IsAuthenticated]


class ResignationUpdateView(generics.UpdateAPIView):
    """PATCH /api/resignations/<pk>/ — update status (restricted to HR / Admin)."""
    queryset = Resignation.objects.all()
    serializer_class = ResignationSerializer
    permission_classes = [IsHROrAdmin]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        status_serializer = ResignationStatusSerializer(data=request.data)
        status_serializer.is_valid(raise_exception=True)
        instance.status = status_serializer.validated_data['status']
        instance.save()
        return Response(ResignationSerializer(instance).data)


@api_view(['GET', 'PUT'])
@permission_classes([IsHROrAdmin])
def settings_view(request):
    """GET/PUT /api/settings/ — read or update singleton settings (restricted to HR / Admin)."""
    settings = SystemSettings.load()

    if request.method == 'GET':
        return Response(SystemSettingsSerializer(settings).data)

    serializer = SystemSettingsSerializer(settings, data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


class AuditLogListCreateView(generics.ListCreateAPIView):
    """GET /api/audit-logs/ — list.  POST — add new entry."""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]


class ResignationWithdrawView(generics.UpdateAPIView):
    """PATCH /api/resignations/<pk>/withdraw/ — withdraw resignation (restricted to owner)."""
    queryset = Resignation.objects.all()
    serializer_class = ResignationSerializer
    permission_classes = [IsAuthenticated]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.email != request.user.email:
            return Response({'error': 'You do not have permission to withdraw this resignation.'}, status=status.HTTP_403_FORBIDDEN)
        instance.status = 'Withdrawn'
        instance.save()
        return Response(ResignationSerializer(instance).data)


from django.db import connection

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


