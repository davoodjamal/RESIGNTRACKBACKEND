from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Resignation
from ..serializers import ResignationSerializer, ResignationFormSerializer


class ResignationListCreateView(generics.ListCreateAPIView):
    """GET /api/resignations/ — list all.  POST — create new."""
    serializer_class = ResignationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['hr', 'admin']:
            return Resignation.objects.all().order_by('-created_at')
        return Resignation.objects.filter(email=user.email).order_by('-created_at')

    def post(self, request, *args, **kwargs):
        reason = request.data.get('reason')
        last_working_day = request.data.get('last_working_day')
        comments = request.data.get('comments', '')

        if not reason or not last_working_day:
            return Response({'error': 'reason and last_working_day are required.'}, status=status.HTTP_400_BAD_REQUEST)

        draft = Resignation.objects.filter(email=request.user.email, status='Draft').order_by('-created_at').first()
        if draft:
            draft.reason = reason
            draft.relieving_date = last_working_day
            draft.comments = comments
            draft.status = 'Pending'
            draft.save()
            resignation = draft
        else:
            resignation = Resignation.objects.create(
                email=request.user.email,
                name=request.user.full_name or request.user.username or 'Alex Thompson',
                department=request.user.designation or 'Design',
                reason=reason,
                relieving_date=last_working_day,
                comments=comments,
                status='Pending'
            )

        return Response({
            "id": resignation.id,
            "status": "SUBMITTED",
            "message": "Resignation submitted successfully"
        }, status=status.HTTP_201_CREATED)


class DashboardSummaryView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        resignation = Resignation.objects.filter(email=request.user.email).exclude(status='Withdrawn').order_by('-created_at').first()
        
        active_resignation = False
        resignation_status = None
        if resignation:
            active_resignation = True
            resignation_status = "SUBMITTED" if resignation.status == 'Pending' else resignation.status.upper()

        return Response({
            "employee_name": request.user.full_name or request.user.username or 'Alex Thompson',
            "employee_id": str(request.user.id),
            "active_resignation": active_resignation,
            "resignation_status": resignation_status,
            "notifications": []
        })


class EmployeeResignationStatusView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        resignation = Resignation.objects.filter(email=request.user.email).exclude(status='Withdrawn').order_by('-created_at').first()
        if not resignation:
            return Response({'error': 'No active resignation found'}, status=status.HTTP_404_NOT_FOUND)
            
        status_str = "SUBMITTED" if resignation.status == 'Pending' else resignation.status.upper()
        submitted_at = ""
        if resignation.submission_date:
            try:
                submitted_at = resignation.submission_date.strftime('%Y-%m-%d')
            except AttributeError:
                submitted_at = resignation.submission_date.date().strftime('%Y-%m-%d')
        
        return Response({
            "status": status_str,
            "submitted_at": submitted_at
        })


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


class ResignationFeedbackView(generics.UpdateAPIView):
    """PATCH /api/resignations/<pk>/feedback/ — save or submit exit interview feedback (restricted to owner)."""
    queryset = Resignation.objects.all()
    serializer_class = ResignationSerializer
    permission_classes = [IsAuthenticated]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.email != request.user.email:
            return Response({'error': 'You do not have permission to update this exit interview.'}, status=status.HTTP_403_FORBIDDEN)
        if 'exitFeedback' in request.data:
            instance.exit_feedback = request.data['exitFeedback']
        elif 'exit_feedback' in request.data:
            instance.exit_feedback = request.data['exit_feedback']
        instance.save()
        return Response(ResignationSerializer(instance).data)


class ResignationDraftView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResignationFormSerializer

    def get(self, request, *args, **kwargs):
        draft = Resignation.objects.filter(email=request.user.email, status='Draft').order_by('-created_at').first()
        if not draft:
            return Response({'error': 'No draft found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(draft)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        draft = Resignation.objects.filter(email=request.user.email, status='Draft').order_by('-created_at').first()
        if draft:
            serializer = self.get_serializer(draft, data=request.data, partial=True)
        else:
            serializer = self.get_serializer(data=request.data)
        
        serializer.is_valid(raise_exception=True)
        serializer.save(status='Draft')
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ResignationDraftUpdateView(generics.UpdateAPIView):
    queryset = Resignation.objects.all()
    serializer_class = ResignationFormSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.email != request.user.email:
            return Response({'error': 'You do not have permission to update this draft.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(status='Draft')
        return Response(serializer.data)


class ResignationSubmitView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResignationFormSerializer

    def post(self, request, *args, **kwargs):
        from ..models import SystemSettings
        draft_id = request.data.get('id')
        draft = None
        if draft_id:
            draft = Resignation.objects.filter(id=draft_id, email=request.user.email).first()
        
        if not draft:
            draft = Resignation.objects.filter(email=request.user.email, status='Draft').order_by('-created_at').first()

        system_settings = SystemSettings.load()
        target_status = 'Approved' if system_settings.auto_approve else 'Pending'

        if draft:
            serializer = self.get_serializer(draft, data=request.data, partial=True)
        else:
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get('reason') or not serializer.validated_data.get('relieving_date'):
            return Response({'error': 'Reason for leaving and proposed last working day are required for submission.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(status=target_status)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResignationDetailView(generics.RetrieveAPIView):
    queryset = Resignation.objects.all()
    serializer_class = ResignationSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.role not in ['hr', 'admin'] and instance.email != request.user.email:
            return Response({'error': 'You do not have permission to view this resignation.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(self.get_serializer(instance).data)

