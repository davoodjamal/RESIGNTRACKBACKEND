from rest_framework import serializers
from ..models import AppUser, SystemSettings, AuditLog

class ResignationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['Pending', 'Approved', 'Rejected', 'Withdrawn', 'More Info Requested'])

class SystemSettingsSerializer(serializers.ModelSerializer):
    noticePeriod = serializers.IntegerField(source='notice_period')
    autoApprove = serializers.BooleanField(source='auto_approve')

    class Meta:
        model = SystemSettings
        fields = ['noticePeriod', 'autoApprove', 'reasons']

class AuditLogSerializer(serializers.ModelSerializer):
    time = serializers.DateTimeField(format='%H:%M:%S', read_only=True)
    timestamp = serializers.SerializerMethodField()
    userId = serializers.IntegerField(source='user_id', required=False, allow_null=True)
    userName = serializers.SerializerMethodField()
    actionType = serializers.CharField(source='action', required=False, allow_blank=True)
    ipAddress = serializers.CharField(source='ip_address', required=False, allow_blank=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'time', 'timestamp', 'userId', 'userName',
            'actionType', 'target', 'ipAddress', 'message'
        ]

    def get_timestamp(self, obj):
        if obj.time:
            return obj.time.isoformat()
        return None

    def get_userName(self, obj):
        if obj.user_id:
            try:
                user = AppUser.objects.get(id=obj.user_id)
                return user.username or user.email
            except AppUser.DoesNotExist:
                pass
        return 'System'
