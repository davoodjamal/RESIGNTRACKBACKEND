from rest_framework import serializers
from ..models import RescheduleRequest, Resignation

class RescheduleRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RescheduleRequest
        fields = [
            'id', 'resignation', 'current_schedule', 'requested_date',
            'requested_time', 'reason', 'status', 'rejection_reason', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'rejection_reason', 'created_at']

    def validate(self, attrs):
        if not attrs.get('resignation'):
            raise serializers.ValidationError({'resignation': 'Resignation ID is required.'})
        if not attrs.get('current_schedule'):
            raise serializers.ValidationError({'current_schedule': 'Current schedule is required.'})
        if not attrs.get('requested_date'):
            raise serializers.ValidationError({'requested_date': 'Requested date is required.'})
        if not attrs.get('requested_time'):
            raise serializers.ValidationError({'requested_time': 'Requested time is required.'})
        if not attrs.get('reason') or not attrs.get('reason').strip():
            raise serializers.ValidationError({'reason': 'Reason for rescheduling is required.'})
        return attrs
