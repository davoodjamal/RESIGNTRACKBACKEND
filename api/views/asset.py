from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, date
from ..models import Asset, AppUser, AuditLog, AssetAuditLog
from ..serializers import AssetSerializer, AppUserSerializer, AssetAuditLogSerializer
from .common import IsHROrAdmin

from rest_framework.permissions import IsAuthenticated

class AssetListCreateView(generics.ListCreateAPIView):
    serializer_class = AssetSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsHROrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role in ['hr', 'admin']:
            return Asset.objects.all().order_by('-created_at')
        return Asset.objects.filter(assigned_to=user).order_by('-created_at')

    def perform_create(self, serializer):
        # Log the registration of asset
        asset = serializer.save()
        AuditLog.objects.create(
            user_id=self.request.user.id if self.request.user.is_authenticated else None,
            action='Asset Registered',
            target=asset.tag,
            message=f"Asset {asset.name} ({asset.tag}) registered. Initial status: {asset.status}."
        )

class AssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer

    def get_permissions(self):
        if self.request.method in ['GET', 'PUT', 'PATCH']:
            return [IsAuthenticated()]
        return [IsHROrAdmin()]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if user.role not in ['hr', 'admin'] and obj.assigned_to != user:
            self.permission_denied(self.request, message="You do not have permission to access this asset.")
        return obj

    def perform_update(self, serializer):
        old_status = self.get_object().status
        asset = serializer.save()
        if old_status != asset.status:
            AuditLog.objects.create(
                user_id=self.request.user.id if self.request.user.is_authenticated else None,
                action='Asset Status Updated',
                target=asset.tag,
                message=f"Asset {asset.tag} status updated from {old_status} to {asset.status}."
            )

class AssetAssignView(APIView):
    permission_classes = [IsHROrAdmin]

    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        try:
            asset = Asset.objects.select_for_update().get(pk=pk)
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

        if asset.status != 'Available':
            return Response({'error': 'Asset is not available for assignment'}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get('email')
        if not email:
            # Check if employee object was sent
            employee_data = request.data.get('employee', {})
            if isinstance(employee_data, dict):
                email = employee_data.get('email')
            else:
                email = employee_data

        if not email:
            return Response({'error': 'Employee email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            employee = AppUser.objects.get(email=email)
        except AppUser.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        # Update Asset
        asset.status = 'Assigned'
        asset.assigned_to = employee
        asset.due_back = date.today() + timedelta(days=30)
        asset.save()

        # Log action
        AuditLog.objects.create(
            user_id=request.user.id if request.user.is_authenticated else None,
            action='Asset Assigned',
            target=asset.tag,
            message=f"Asset {asset.name} ({asset.tag}) assigned to {employee.full_name or employee.username} ({employee.email})."
        )

        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

class AssetReturnView(APIView):
    permission_classes = [IsHROrAdmin]

    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        try:
            asset = Asset.objects.select_for_update().get(pk=pk)
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

        if asset.status != 'Assigned':
            return Response({'error': 'Asset is not currently assigned'}, status=status.HTTP_400_BAD_REQUEST)

        employee = asset.assigned_to
        emp_email = employee.email if employee else 'Unknown'
        emp_name = (employee.full_name or employee.username) if employee else 'Unknown'

        # Extract return details
        condition = request.data.get('condition', 'Good')
        remarks = request.data.get('remarks', 'Returned to inventory')

        # Reset Asset
        asset.status = 'Available'
        asset.assigned_to = None
        asset.due_back = None
        if remarks:
            asset.maintenance_notes = f"Returned in {condition} condition. Notes: {remarks}"
        asset.save()

        # Log action
        AuditLog.objects.create(
            user_id=request.user.id if request.user.is_authenticated else None,
            action='Asset Returned',
            target=asset.tag,
            message=f"Asset {asset.name} ({asset.tag}) returned by {emp_name} ({emp_email}). Condition: {condition}. Remarks: {remarks}."
        )

        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

class AssetMaintenanceView(APIView):
    permission_classes = [IsHROrAdmin]

    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        try:
            asset = Asset.objects.select_for_update().get(pk=pk)
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

        target_status = request.data.get('status')
        if not target_status:
            # Toggle maintenance state
            if asset.status == 'Under Maintenance':
                target_status = 'Available'
            else:
                target_status = 'Under Maintenance'

        if target_status == 'Under Maintenance' and asset.status == 'Assigned':
            return Response({'error': 'Cannot put assigned asset into maintenance. Return it first.'}, status=status.HTTP_400_BAD_REQUEST)
        if target_status == 'Disposed' and asset.status == 'Assigned':
            return Response({'error': 'Cannot dispose assigned asset. Return it first.'}, status=status.HTTP_400_BAD_REQUEST)

        old_status = asset.status
        asset.status = target_status
        if target_status in ['Under Maintenance', 'Disposed']:
            asset.assigned_to = None
            asset.due_back = None
            action_label = 'Moved to maintenance' if target_status == 'Under Maintenance' else 'Disposed'
            notes = request.data.get('notes', action_label)
            if notes:
                asset.maintenance_notes = notes
        asset.save()

        # Log action
        AuditLog.objects.create(
            user_id=request.user.id if request.user.is_authenticated else None,
            action='Asset Maintenance' if target_status == 'Under Maintenance' else 'Asset Disposed',
            target=asset.tag,
            message=f"Asset {asset.name} ({asset.tag}) status changed from {old_status} to {asset.status}."
        )

        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

class AssetDashboardView(APIView):
    permission_classes = [IsHROrAdmin]

    def get(self, request, *args, **kwargs):
        assets = Asset.objects.all()
        total = assets.count()
        available = assets.filter(status='Available').count()
        assigned = assets.filter(status='Assigned').count()
        maintenance = assets.filter(status='Under Maintenance').count()
        
        # Overdue returns: status is Assigned and due_back < today
        today = timezone.now().date()
        overdue_count = assets.filter(status='Assigned', due_back__lt=today).count()
        
        # Warranty expiring: warranty_expiry within 45 days
        expiring_soon = assets.filter(
            warranty_expiry__gte=today,
            warranty_expiry__lte=today + timedelta(days=45)
        ).count()

        return Response({
            'total': total,
            'available': available,
            'assigned': assigned,
            'maintenance': maintenance,
            'overdueCount': overdue_count,
            'warrantyExpiringSoonCount': expiring_soon
        })

class EmployeeListView(APIView):
    permission_classes = [IsHROrAdmin]

    def get(self, request, *args, **kwargs):
        employees = AppUser.objects.filter(role='employee')
        data = []
        for emp in employees:
            data.append({
                'id': emp.id,
                'name': emp.full_name or emp.username,
                'role': emp.designation or 'Employee',
                'email': emp.email
            })
        return Response(data)

class AssetAuditLogListView(generics.ListAPIView):
    """GET /api/assets/audit/ - List all asset audit log entries."""
    queryset = AssetAuditLog.objects.all().order_by('-date', '-id')
    serializer_class = AssetAuditLogSerializer
    permission_classes = [IsHROrAdmin]
