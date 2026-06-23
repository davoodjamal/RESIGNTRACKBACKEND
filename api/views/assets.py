from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import datetime

from ..models import Asset, AssetAuditLog, AppUser, Notification
from ..serializers import AssetSerializer, AssetAuditLogSerializer
from .common import IsHROrAdmin

class AssetListCreateView(generics.ListCreateAPIView):
    """GET /api/assets/ - List assets. POST /api/assets/ - Create asset."""
    serializer_class = AssetSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsHROrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role in ['hr', 'admin']:
            return Asset.objects.all().order_by('-created_at')
        return Asset.objects.filter(assigned_to=user.email).order_by('-created_at')

class AssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE /api/assets/<pk>/ - Manage asset details."""
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer

    def get_permissions(self):
        if self.request.method in ['GET', 'PUT', 'PATCH']:
            return [IsAuthenticated()]
        return [IsHROrAdmin()]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if user.role not in ['hr', 'admin'] and obj.assigned_to != user.email:
            self.permission_denied(self.request, message="You do not have permission to access this asset.")
        return obj


class AssetAssignView(generics.GenericAPIView):
    """POST /api/assets/<pk>/assign/ - Assign an asset to an employee."""
    queryset = Asset.objects.all()
    permission_classes = [IsHROrAdmin]

    def post(self, request, pk, *args, **kwargs):
        asset = self.get_object()
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        asset.status = 'Assigned'
        asset.assigned_to = email
        # Let's set a default due back date, e.g. in 30 days or TBD
        asset.due_back = datetime.date.today() + datetime.timedelta(days=30)
        asset.save()

        # Log audit trail
        performed_by = request.user.email if request.user else 'System'
        AssetAuditLog.objects.create(
            asset_id=asset.id,
            asset_tag=asset.tag,
            action='Assign',
            performed_by=performed_by,
            notes=f"Assigned to {email}"
        )

        # Notify Employee
        employee = AppUser.objects.filter(email=email).first()
        if employee:
            Notification.objects.create(
                user=employee,
                title="Asset Assigned",
                message=f"Asset '{asset.name}' (Tag: {asset.tag}) has been assigned to you. Due Back: {asset.due_back}",
                icon="inventory_2"
            )

        return Response(AssetSerializer(asset).data)

class AssetReturnView(generics.GenericAPIView):
    """POST /api/assets/<pk>/return/ - Return an asset back to inventory."""
    queryset = Asset.objects.all()
    permission_classes = [IsHROrAdmin]

    def post(self, request, pk, *args, **kwargs):
        asset = self.get_object()
        previous_assigned_to = asset.assigned_to
        
        return_date = request.data.get('returnDate', datetime.date.today().isoformat())
        condition = request.data.get('condition', 'Good')
        remarks = request.data.get('remarks', 'Returned to inventory')

        performed_by = request.user.email if request.user else 'System'
        
        # Log audit trail
        AssetAuditLog.objects.create(
            asset_id=asset.id,
            asset_tag=asset.tag,
            action='Return',
            performed_by=performed_by,
            notes=f"Returned on {return_date}. Condition: {condition}. Remarks: {remarks}"
        )

        asset.status = 'Available'
        asset.assigned_to = ''
        asset.due_back = None
        if condition == 'Damaged':
            asset.status = 'Under Maintenance'
            asset.notes = f"Returned Damaged. Remarks: {remarks}"
        elif condition == 'Lost':
            asset.status = 'Retired'
            asset.notes = f"Returned Lost. Remarks: {remarks}"
        asset.save()

        # Notify Employee
        if previous_assigned_to:
            employee = AppUser.objects.filter(email=previous_assigned_to).first()
            if employee:
                Notification.objects.create(
                    user=employee,
                    title="Asset Returned",
                    message=f"Asset '{asset.name}' (Tag: {asset.tag}) has been successfully returned.",
                    icon="inventory_2"
                )

        return Response(AssetSerializer(asset).data)

class AssetAuditLogListView(generics.ListAPIView):
    """GET /api/assets/audit/ - List all asset audit log entries."""
    queryset = AssetAuditLog.objects.all().order_by('-date', '-id')
    serializer_class = AssetAuditLogSerializer
    permission_classes = [IsHROrAdmin]

