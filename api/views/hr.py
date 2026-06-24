from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import AppUser, Resignation, SystemSettings, AuditLog
from ..serializers import (
    ResignationSerializer,
    ResignationStatusSerializer,
    SystemSettingsSerializer,
    AuditLogSerializer,
)
from .common import IsHROrAdmin


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
@permission_classes([IsAuthenticated])
def settings_view(request):
    """GET/PUT /api/settings/ — read or update singleton settings."""
    if request.method == 'PUT':
        if not (request.user and request.user.is_authenticated and request.user.role in ['hr', 'admin']):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
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

    def perform_create(self, serializer):
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(user_id=self.request.user.id)
        else:
            serializer.save()


from rest_framework.views import APIView
from django.utils import timezone
from .employee_detail import EmployeeDetailView

class ResignationProcessView(APIView):
    permission_classes = [IsHROrAdmin]

    def put(self, request, *args, **kwargs):
        employee_id = request.data.get('employeeId')
        action = request.data.get('action')
        remarks = request.data.get('remarks', '')

        if not employee_id:
            return Response({'error': 'employeeId is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not action or action not in ['APPROVE', 'REJECT', 'REQUEST_INFO']:
            return Response({'error': 'Valid action (APPROVE, REJECT, or REQUEST_INFO) is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = AppUser.objects.get(pk=employee_id)
        except AppUser.DoesNotExist:
            return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)

        resignation = Resignation.objects.filter(email=user.email).order_by('-created_at').first()
        if not resignation:
            return Response({'error': 'No active resignation found for this employee.'}, status=status.HTTP_404_NOT_FOUND)

        if resignation.status in ['Approved', 'Rejected']:
            return Response({'error': 'Resignation process has already been finalized.'}, status=status.HTTP_400_BAD_REQUEST)

        # Map action to resignation status
        status_map = {
            'APPROVE': 'Approved',
            'REJECT': 'Rejected',
            'REQUEST_INFO': 'More Info Requested',
        }
        resignation.status = status_map[action]
        
        # Log comments if provided
        if remarks:
            if not isinstance(resignation.exit_feedback, dict):
                resignation.exit_feedback = {}
            resignation.exit_feedback['hr_remarks'] = remarks
                
        resignation.save()

        # Create AuditLog entry
        AuditLog.objects.create(
            user_id=request.user.id if request.user and request.user.is_authenticated else None,
            action='Review Finalized' if action in ['APPROVE', 'REJECT'] else 'More Info Requested',
            target=f"Employee: {user.username} ({user.email})",
            message=f"Action: {action}. Remarks: {remarks}"
        )

        # Delegate details generation to EmployeeDetailView
        view = EmployeeDetailView()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {'pk': user.id}
        return view.retrieve(request)

