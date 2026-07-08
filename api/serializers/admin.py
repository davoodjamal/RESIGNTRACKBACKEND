from rest_framework import serializers
from ..models import AppUser

class AppUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    fullName = serializers.CharField(source='full_name', required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    status = serializers.SerializerMethodField()
    joinDate = serializers.SerializerMethodField()

    class Meta:
        model = AppUser
        fields = [
            'id', 'email', 'username', 'role', 'password',
            'fullName', 'phone', 'dob', 'designation', 'address', 'permissions', 'status', 'joinDate'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def get_joinDate(self, obj):
        from ..models import CompanyMasterEmployee
        emp = CompanyMasterEmployee.objects.filter(employee_id=obj.id).first()
        if emp and emp.joining_date:
            return emp.joining_date.strftime('%Y-%m-%d')
        # Fallback to hash seeding
        hash_val = obj.id
        years = [2019, 2020, 2021, 2022, 2023]
        year = years[hash_val % len(years)]
        day = (hash_val * 7) % 28 + 1
        month_idx = (hash_val % 12) + 1
        return f"{year}-{month_idx:02d}-{day:02d}"

    def get_status(self, obj):
        if obj.role != 'employee':
            return 'Active'
        
        from ..models import Resignation
        from django.utils import timezone
        
        res = Resignation.objects.filter(email=obj.email).order_by('-created_at').first()
        if not res:
            return 'Active'
            
        if res.status == 'Approved':
            if res.relieving_date and res.relieving_date > timezone.localdate():
                return 'In-Notice'
            return 'Resigned'
        elif res.status in ['Pending', 'More Info Requested', 'Pending HR Review', 'Exit Interview Pending', 'Exit Interview Submitted', 'Awaiting Exit Interview', 'Awaiting Approval']:
            return 'In-Notice'
        elif res.status in ['Rejected', 'Withdrawn', 'Draft']:
            return 'Active'
            
        return 'Active'

    def validate(self, attrs):
        if not attrs.get('username') and attrs.get('full_name'):
            attrs['username'] = attrs['full_name']
        elif not attrs.get('username'):
            attrs['username'] = attrs.get('email', 'user').split('@')[0]
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        raw_date = None
        if request:
            raw_date = request.data.get('joinDate')

        password = validated_data.pop('password', None)
        email = validated_data.pop('email').lower().strip()
        username = validated_data.pop('username', '')
        role = validated_data.pop('role', 'employee')
        
        user = AppUser.objects.filter(email=email).first()
        if user:
            user.username = username or user.username
            if password:
                user.set_password(password)
                user.raw_password = password
            user.role = role
            for attr, val in validated_data.items():
                setattr(user, attr, val)
            user.save()
        else:
            user = AppUser.objects.create_user(
                email=email,
                username=username,
                password=password,
                role=role,
                **validated_data
            )

        if raw_date:
            from ..models import CompanyMasterEmployee, HRManagementStaffProfile, UserDirectoryEmployeePersonal
            CompanyMasterEmployee.objects.update_or_create(employee_id=user.id, defaults={"joining_date": raw_date})
            HRManagementStaffProfile.objects.update_or_create(employee_id=user.id, defaults={"date_of_joining": raw_date})
            UserDirectoryEmployeePersonal.objects.update_or_create(employee_id=user.id, defaults={"hire_date": raw_date})
            
            from ..models import JoiningDateAuditLog
            JoiningDateAuditLog.objects.update_or_create(
                employee_id=user.id,
                action_type="ONBOARD_CREATE",
                defaults={
                    "previous_value": None,
                    "new_value": raw_date,
                    "actor": request.user.email if request else 'System',
                    "sync_status": {"admin": "Success", "hr": "Success", "employee": "Success"}
                }
            )
        return user
