from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Resignation
from ..serializers import ResignationSerializer


class ResignationListCreateView(generics.ListCreateAPIView):
    """GET /api/resignations/ — list all.  POST — create new."""
    queryset = Resignation.objects.all().order_by('-created_at')
    serializer_class = ResignationSerializer
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
