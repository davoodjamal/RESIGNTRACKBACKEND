from rest_framework import serializers
from .models import AppUser, Resignation, SystemSettings, AuditLog


class AppUserSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source='full_name', required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = AppUser
        fields = [
            'id', 'email', 'username', 'role', 'password',
            'fullName', 'phone', 'dob', 'designation', 'address', 'permissions'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        if not attrs.get('username') and attrs.get('full_name'):
            attrs['username'] = attrs['full_name']
        elif not attrs.get('username'):
            attrs['username'] = attrs.get('email', 'user').split('@')[0]
        return attrs



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    role = serializers.CharField()


class ResignationSerializer(serializers.ModelSerializer):
    # Accept camelCase from frontend, map to snake_case model fields
    submissionDate = serializers.DateField(source='submission_date', read_only=True)
    relievingDate = serializers.DateField(source='relieving_date')
    exitFeedback = serializers.JSONField(source='exit_feedback', required=False)

    class Meta:
        model = Resignation
        fields = [
            'id', 'email', 'name', 'department', 'reason',
            'submissionDate', 'relievingDate', 'comments', 'status', 'exitFeedback'
        ]


class ResignationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['Pending', 'Approved', 'Rejected', 'Withdrawn'])


class SystemSettingsSerializer(serializers.ModelSerializer):
    noticePeriod = serializers.IntegerField(source='notice_period')
    autoApprove = serializers.BooleanField(source='auto_approve')

    class Meta:
        model = SystemSettings
        fields = ['noticePeriod', 'autoApprove', 'reasons']


class AuditLogSerializer(serializers.ModelSerializer):
    time = serializers.DateTimeField(format='%H:%M:%S', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'time', 'message']
