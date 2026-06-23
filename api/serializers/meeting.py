from rest_framework import serializers
from ..models import Meeting, AppUser

class MeetingSerializer(serializers.ModelSerializer):
    employeeId = serializers.PrimaryKeyRelatedField(source='employee', queryset=AppUser.objects.all())
    employeeName = serializers.SerializerMethodField()
    employeeEmail = serializers.CharField(source='employee.email', read_only=True)
    timeSlot = serializers.CharField(source='time_slot')
    jitsiUrl = serializers.CharField(source='jitsi_url')

    class Meta:
        model = Meeting
        fields = ['id', 'employeeId', 'employeeName', 'employeeEmail', 'date', 'timeSlot', 'jitsiUrl', 'created_at']

    def get_employeeName(self, obj):
        return obj.employee.full_name or obj.employee.username

    def validate_jitsiUrl(self, value):
        val = value.strip()
        if not val.startswith('https://meet.jit.si/') and not val.startswith('https://'):
            raise serializers.ValidationError("Jitsi URL must start with 'https://meet.jit.si/' or 'https://'")
        return val
