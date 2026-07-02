from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import datetime

from ..models import RescheduleRequest, Resignation, AuditLog
from ..serializers import RescheduleRequestSerializer
from .common import IsHROrAdmin

class RescheduleRequestCreateView(generics.ListCreateAPIView):
    """
    GET /api/resignations/reschedule/ — list requests for employee.
    POST /api/resignations/reschedule/ — submit a reschedule request.
    """
    serializer_class = RescheduleRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['hr', 'admin']:
            return RescheduleRequest.objects.all().order_by('-created_at')
        return RescheduleRequest.objects.filter(resignation__email=user.email).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        resignation_id = request.data.get('resignation')
        if not resignation_id:
            return Response({'error': 'Resignation ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        resignation = get_object_or_404(Resignation, id=resignation_id)
        
        # Block duplicate reschedule requests while one is pending
        pending_exists = RescheduleRequest.objects.filter(
            resignation=resignation,
            status='Pending'
        ).exists()
        if pending_exists:
            return Response(
                {'error': 'A reschedule request is already pending for this consultation.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reschedule_req = serializer.save()

        # Update meeting status on resignation
        resignation.meeting_status = 'Reschedule Requested'
        resignation.save()

        # Add audit log
        req_date = reschedule_req.requested_date.strftime('%Y-%m-%d')
        req_time = reschedule_req.requested_time.strftime('%H:%M')
        AuditLog.objects.create(
            user_id=request.user.id if request.user else None,
            message=f"Exit interview reschedule requested: Employee [{resignation.email}] requested to move meeting from {reschedule_req.current_schedule} to {req_date} at {req_time}. Reason: {reschedule_req.reason}",
            target=resignation.email
        )

        return Response(RescheduleRequestSerializer(reschedule_req).data, status=status.HTTP_201_CREATED)

class RescheduleRequestListView(generics.ListAPIView):
    """
    GET /api/resignations/reschedule/list/ — HR lists all reschedule requests.
    """
    queryset = RescheduleRequest.objects.all().order_by('-created_at')
    serializer_class = RescheduleRequestSerializer
    permission_classes = [IsHROrAdmin]

class RescheduleRequestDecisionView(generics.GenericAPIView):
    """
    POST /api/resignations/reschedule/<pk>/decision/ — HR decides on a reschedule request (Approve/Reject).
    """
    queryset = RescheduleRequest.objects.all()
    serializer_class = RescheduleRequestSerializer
    permission_classes = [IsHROrAdmin]

    def post(self, request, pk, *args, **kwargs):
        reschedule_req = self.get_object()
        decision = request.data.get('decision') # 'Approved' or 'Rejected'
        rejection_reason = request.data.get('rejection_reason', '')

        if decision not in ['Approved', 'Rejected']:
            return Response({'error': 'Decision must be Approved or Rejected'}, status=status.HTTP_400_BAD_REQUEST)

        reschedule_req.status = decision
        if decision == 'Rejected':
            reschedule_req.rejection_reason = rejection_reason
        reschedule_req.save()

        resignation = reschedule_req.resignation

        if decision == 'Approved':
            # Format the new schedule string
            new_date = reschedule_req.requested_date.strftime('%Y-%m-%d')
            new_time = reschedule_req.requested_time.strftime('%I:%M %p') # e.g. "02:00 PM"
            new_schedule = f"{new_date}, {new_time}"

            resignation.meeting_schedule = new_schedule
            resignation.meeting_status = 'Scheduled'
            resignation.save()

            AuditLog.objects.create(
                user_id=request.user.id if request.user else None,
                message=f"Reschedule request approved: HR moved exit interview for [{resignation.email}] to {new_schedule}.",
                target=resignation.email
            )
        else: # Rejected
            resignation.meeting_status = 'Scheduled' # Revert back to Scheduled
            resignation.save()

            AuditLog.objects.create(
                user_id=request.user.id if request.user else None,
                message=f"Reschedule request rejected: HR declined reschedule for [{resignation.email}]. Reason: {rejection_reason}",
                target=resignation.email
            )

        return Response(RescheduleRequestSerializer(reschedule_req).data)
