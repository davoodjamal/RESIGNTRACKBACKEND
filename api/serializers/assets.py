from rest_framework import serializers
from ..models import Asset, AssetAuditLog

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'id', 'tag', 'name', 'type', 'status',
            'assigned_to', 'due_back', 'warranty_expiry', 'notes', 'created_at'
        ]

class AssetAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAuditLog
        fields = [
            'id', 'asset_id', 'asset_tag', 'action',
            'performed_by', 'date', 'notes'
        ]
