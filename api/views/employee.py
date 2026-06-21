from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Resignation
from ..serializers import ResignationSerializer


class ResignationListCreateView(generics.ListCreateAPIView):
    """GET /api/resignations/ — list all.  POST — create new."""
    serializer_class = ResignationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['hr', 'admin']:
            return Resignation.objects.all().order_by('-created_at')
        return Resignation.objects.filter(email=user.email).order_by('-created_at')


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
