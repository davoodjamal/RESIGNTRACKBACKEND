from rest_framework import serializers
from ..models import Asset, AppUser, AssetAuditLog

class AssetSerializer(serializers.ModelSerializer):
    assignedTo = serializers.SerializerMethodField()
    dueBack = serializers.DateField(source='due_back', required=False, allow_null=True)
    warrantyExpiry = serializers.DateField(source='warranty_expiry', required=False, allow_null=True)
    maintenanceNotes = serializers.CharField(source='maintenance_notes', required=False, allow_blank=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'tag', 'name', 'type', 'status',
            'assignedTo', 'dueBack', 'warrantyExpiry', 'maintenanceNotes'
        ]

    def get_assignedTo(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.email
        return ''

class AssetAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAuditLog
        fields = [
            'id', 'asset_id', 'asset_tag', 'action',
            'performed_by', 'date', 'notes'
        ]
