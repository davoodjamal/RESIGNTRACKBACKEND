from django.db import connection
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from ..models import AppUser, Resignation
from ..serializers import AppUserSerializer
from .common import IsHROrAdmin


class UserListView(generics.ListCreateAPIView):
    """GET /api/users/ — list all users. POST — create new user (restricted to HR / Admin)."""
    serializer_class = AppUserSerializer
    permission_classes = [IsHROrAdmin]

    def get_queryset(self):
        queryset = AppUser.objects.all()
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            from ..models import Resignation
            from django.utils import timezone
            status_filter_lower = status_filter.lower()
            if status_filter_lower != 'all':
                filtered_users = []
                for user in queryset:
                    res = Resignation.objects.filter(email=user.email).order_by('-created_at').first()
                    user_status = 'active'
                    if res:
                        if res.status == 'Approved':
                            if res.relieving_date and res.relieving_date > timezone.localdate():
                                user_status = 'in-notice'
                            else:
                                user_status = 'resigned'
                        elif res.status in ['Pending', 'More Info Requested', 'Pending HR Review', 'Exit Interview Pending', 'Exit Interview Submitted', 'Awaiting Exit Interview', 'Awaiting Approval']:
                            user_status = 'in-notice'
                        elif res.status in ['Rejected', 'Withdrawn', 'Draft']:
                            user_status = 'active'
                    
                    if status_filter_lower in ['in notice', 'in-notice']:
                        match = (user_status == 'in-notice')
                    else:
                        match = (user_status == status_filter_lower)
                    
                    if match:
                        filtered_users.append(user.id)
                queryset = queryset.filter(id__in=filtered_users)

        return queryset

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
