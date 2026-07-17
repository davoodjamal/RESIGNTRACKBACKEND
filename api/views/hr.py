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
    permission_classes = [IsHROrAdmin]

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
        notice_period = request.data.get('noticePeriod')

        if not employee_id:
            return Response({'error': 'employeeId is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not action or action not in ['APPROVE', 'REJECT', 'REQUEST_INFO', 'INITIATE_INTERVIEW', 'UPDATE_NOTICE_PERIOD', 'COMPLETE_MEETING', 'EMERGENCY_RELEASE']:
            return Response({'error': 'Valid action (APPROVE, REJECT, REQUEST_INFO, INITIATE_INTERVIEW, UPDATE_NOTICE_PERIOD, COMPLETE_MEETING, or EMERGENCY_RELEASE) is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = AppUser.objects.get(pk=employee_id)
        except AppUser.DoesNotExist:
            return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)

        resignation = Resignation.objects.filter(email=user.email).order_by('-created_at').first()
        if not resignation:
            return Response({'error': 'No active resignation found for this employee.'}, status=status.HTTP_404_NOT_FOUND)

        if resignation.status in ['Approved', 'Rejected']:
            return Response({'error': 'Resignation process has already been finalized.'}, status=status.HTTP_400_BAD_REQUEST)

        # Handle notice period update/recalculation
        if notice_period:
            try:
                days = int(notice_period)
                if days in [15, 30, 45]:
                    if not isinstance(resignation.exit_feedback, dict):
                        resignation.exit_feedback = {}
                    resignation.exit_feedback['notice_period'] = days
                    
                    # Store original proposed last working day if not already stored
                    if 'original_proposed_last_working_day' not in resignation.exit_feedback:
                        resignation.exit_feedback['original_proposed_last_working_day'] = resignation.relieving_date.strftime('%Y-%m-%d') if resignation.relieving_date else resignation.submission_date.strftime('%Y-%m-%d')
                    
                    # Recalculate relieving date
                    resignation.relieving_date = resignation.submission_date + timezone.timedelta(days=days)
            except Exception as e:
                return Response({'error': f'Failed to update notice period: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        # Map action to resignation status
        status_map = {
            'APPROVE': 'Approved',
            'REJECT': 'Rejected',
            'REQUEST_INFO': 'More Info Requested',
            'INITIATE_INTERVIEW': 'Exit Interview Pending',
            'COMPLETE_MEETING': 'Awaiting Approval',
            'EMERGENCY_RELEASE': 'Approved',
        }
        if action in status_map:
            resignation.status = status_map[action]
            if action == 'EMERGENCY_RELEASE':
                resignation.relieving_date = timezone.localdate()
        
        # Log comments if provided
        if remarks:
            if not isinstance(resignation.exit_feedback, dict):
                resignation.exit_feedback = {}
            resignation.exit_feedback['hr_remarks'] = remarks
                
        resignation.save()

        # Handle notifications for Exit Interview Initiation
        if action == 'INITIATE_INTERVIEW':
            from ..models import Notification
            Notification.objects.create(
                user=user,
                title="Exit Interview Unlocked",
                message="HR has initiated your exit interview. Please complete the confidential survey in your portal.",
                icon="fact_check"
            )
            # Simulate email dispatch
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Email sent to {user.email}: Exit Interview Unlocked")

        # Create AuditLog entry
        if action == 'UPDATE_NOTICE_PERIOD':
            AuditLog.objects.create(
                user_id=request.user.id if request.user and request.user.is_authenticated else None,
                action='Policy Modified',
                target=f"Employee: {user.username} ({user.email})",
                message=f"Notice period updated to {notice_period} days. Recalculated relieving date to {resignation.relieving_date}."
            )
        else:
            AuditLog.objects.create(
                user_id=request.user.id if request.user and request.user.is_authenticated else None,
                action='Review Finalized' if action in ['APPROVE', 'REJECT', 'EMERGENCY_RELEASE'] else ('Exit Interview Initiated' if action == 'INITIATE_INTERVIEW' else ('Meeting Completed' if action == 'COMPLETE_MEETING' else 'More Info Requested')),
                target=f"Employee: {user.username} ({user.email})",
                message=f"Action: {action}. Remarks: {remarks}"
            )

        # Delegate details generation to EmployeeDetailView
        view = EmployeeDetailView()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {'pk': user.id}
        return view.retrieve(request)

