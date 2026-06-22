from django.db import connection
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from ..models import AppUser, Resignation
from ..serializers import AppUserSerializer
from .common import IsHROrAdmin


class UserListView(generics.ListCreateAPIView):
    """GET /api/users/ — list all users. POST — create new user (restricted to HR / Admin)."""
    queryset = AppUser.objects.all()
    serializer_class = AppUserSerializer
    permission_classes = [IsHROrAdmin]

    def perform_create(self, serializer):
        serializer.save()


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE /api/users/<pk>/ — manage user details (restricted to HR / Admin)."""
    queryset = AppUser.objects.all()
    serializer_class = AppUserSerializer
    permission_classes = [IsHROrAdmin]

    def perform_update(self, serializer):
        user = serializer.save()
        if 'password' in serializer.validated_data:
            user.set_password(serializer.validated_data['password'])
            user.raw_password = serializer.validated_data['password']
            user.save()


class DashboardMetricsView(APIView):
    permission_classes = [IsHROrAdmin]

    def get(self, request, *args, **kwargs):
        active_count = Resignation.objects.exclude(status__in=['Completed', 'Rejected', 'Archived']).count()
        pending_count = Resignation.objects.filter(status='Pending').count()
        return Response({
            "success": True,
            "data": {
                "activeResignations": active_count,
                "pendingTasks": pending_count
            }
        }, status=status.HTTP_200_OK)


class SystemHealthView(APIView):
    permission_classes = [IsHROrAdmin]

    def get(self, request, *args, **kwargs):
        db_ok = True
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False

        status_str = "Healthy" if db_ok else "Unhealthy"
        errors_count = 0 if db_ok else 1

        return Response({
            "success": True,
            "data": {
                "status": status_str,
                "errors": errors_count,
                "uptime": "99.9%"
            }
        }, status=status.HTTP_200_OK)
