from rest_framework import generics

from ..models import AppUser
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
                            if res.relieving_date and res.relieving_date < timezone.now().date():
                                user_status = 'resigned'
                            else:
                                user_status = 'in-notice'
                        elif res.status == 'Pending':
                            user_status = 'in-notice'
                        elif res.status == 'Rejected' or res.status == 'Withdrawn':
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
            user.raw_password = serializer.validated_data['password']
            user.save()
