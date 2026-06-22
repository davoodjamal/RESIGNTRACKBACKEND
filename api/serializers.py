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

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        email = validated_data.pop('email')
        username = validated_data.pop('username', '')
        role = validated_data.pop('role', 'employee')
        
        user = AppUser.objects.create_user(
            email=email,
            username=username,
            password=password,
            role=role,
            **validated_data
        )
        return user



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
