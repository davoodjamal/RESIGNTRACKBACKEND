from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Resignation, SystemSettings, AuditLog
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
