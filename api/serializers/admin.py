from rest_framework import serializers
from ..models import AppUser

class AppUserSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source='full_name', required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = AppUser
        fields = [
            'id', 'email', 'username', 'role', 'password',
            'fullName', 'phone', 'dob', 'designation', 'address', 'permissions', 'status'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def get_status(self, obj):
        if obj.role != 'employee':
            return 'Active'
        
        from ..models import Resignation
        from django.utils import timezone
        
        res = Resignation.objects.filter(email=obj.email).order_by('-created_at').first()
        if not res:
            return 'Active'
            
        if res.status == 'Approved':
            return 'Resigned'
        elif res.status in ['Pending', 'More Info Requested']:
            return 'In-Notice'
        elif res.status in ['Rejected', 'Withdrawn']:
            return 'Active'
            
        return 'Active'

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
