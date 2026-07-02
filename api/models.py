from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
import json


class AppUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, role='employee', **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(
            email=self.normalize_email(email),
            username=username,
            role=role,
            **extra_fields
        )
        user.set_password(password)
        if password:
            user.raw_password = password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        user = self.create_user(
            email,
            username=username,
            password=password,
            role='admin',
            **extra_fields
        )
        user.save(using=self._db)
        return user


class AppUser(AbstractBaseUser):
    """Application user with role-based access."""
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('hr', 'HR Manager'),
        ('admin', 'Admin'),
    ]
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')

    # Profile & settings fields
    full_name = models.CharField(max_length=200, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    dob = models.DateField(null=True, blank=True)
    designation = models.CharField(max_length=200, blank=True, default='')
    address = models.TextField(blank=True, default='')
    permissions = models.JSONField(default=list, blank=True)
    raw_password = models.CharField(max_length=200, blank=True, default='')

    objects = AppUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        app_label = 'api'

    @property
    def is_staff(self):
        return self.role in ['admin', 'hr']

    @property
    def is_superuser(self):
        return self.role == 'admin'

    @property
    def is_active(self):
        return True

    def has_perm(self, perm, obj=None):
        return self.role == 'admin'

    def has_module_perms(self, app_label):
        return self.role == 'admin'

    def __str__(self):
        return f"{self.username} ({self.role})"


class Resignation(models.Model):
    """Employee resignation request."""
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Awaiting Exit Interview', 'Awaiting Exit Interview'),
        ('Pending', 'Pending'),
        ('Pending HR Review', 'Pending HR Review'),
        ('Exit Interview Pending', 'Exit Interview Pending'),
        ('Exit Interview Submitted', 'Exit Interview Submitted'),
        ('Awaiting Approval', 'Awaiting Approval'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Withdrawn', 'Withdrawn'),
        ('More Info Requested', 'More Info Requested'),
    ]
    email = models.EmailField()
    name = models.CharField(max_length=200)
    department = models.CharField(max_length=200, default='')
    reason = models.CharField(max_length=300, null=True, blank=True)
    submission_date = models.DateField(auto_now_add=True)
    relieving_date = models.DateField(null=True, blank=True)
    comments = models.TextField(blank=True, default='')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')
    exit_feedback = models.JSONField(default=dict, blank=True)
    meeting_schedule = models.CharField(max_length=200, default='Today, 2:00 PM')
    meeting_status = models.CharField(max_length=100, default='Scheduled')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.status}"


class SystemSettings(models.Model):
    """Singleton system configuration."""
    notice_period = models.IntegerField(default=30)
    auto_approve = models.BooleanField(default=False)
    reasons = models.JSONField(default=list)

    class Meta:
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"System Settings (Notice: {self.notice_period} days)"

    def save(self, *args, **kwargs):
        # Enforce singleton: always use pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'notice_period': 30,
                'auto_approve': False,
                'reasons': [
                    'Career Growth', 'Better Opportunity', 'Higher Education',
                    'Health & Medical', 'Personal Reasons', 'Other'
                ]
            }
        )
        return obj


class AuditLog(models.Model):
    """Timestamped audit trail entry."""
    time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('AppUser', on_delete=models.SET_NULL, null=True, blank=True, db_column='user_id')
    action = models.CharField(max_length=100, blank=True, default='SYSTEM_EVENT')
    target = models.CharField(max_length=300, blank=True, default='')
    ip_address = models.CharField(max_length=45, blank=True, default='127.0.0.1')
    message = models.TextField()

    class Meta:
        ordering = ['-time']

    def save(self, *args, **kwargs):
        if (self.action == 'SYSTEM_EVENT' or not self.action) and self.message:
            msg = self.message.lower()
            if 'session opened' in msg or 'logged in' in msg or 'access granted' in msg:
                self.action = 'Access Granted'
            elif 'session closed' in msg or 'signed out' in msg:
                self.action = 'User Removed'
            elif 'export' in msg:
                self.action = 'System Export'
            elif 'removed' in msg or 'delete' in msg:
                self.action = 'User Removed'
            elif 'setting' in msg or 'config' in msg or 'policy' in msg:
                self.action = 'Policy Modified'
            elif 'approved' in msg or 'rejected' in msg or 'review' in msg:
                self.action = 'Review Finalized'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.time}] {self.message[:60]}"


class Asset(models.Model):
    tag = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100)  # Laptop, Monitor, Mobile, Access Card
    status = models.CharField(max_length=50, default='Available')  # Available, Assigned, Under Maintenance
    assigned_to = models.ForeignKey('AppUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets')
    due_back = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    maintenance_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tag} - {self.name}"


class ExitChecklistTask(models.Model):
    STATUS_CHOICES = [
        ('Completed', 'Completed'),
        ('Pending', 'Pending'),
        ('Scheduled', 'Scheduled'),
    ]
    resignation = models.ForeignKey(Resignation, on_delete=models.CASCADE, related_name='checklist_tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    department = models.CharField(max_length=100, blank=True, default='')
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.resignation.email} - {self.title} ({self.status})"


class Meeting(models.Model):
    employee = models.ForeignKey('AppUser', on_delete=models.CASCADE, related_name='meetings')
    date = models.DateField()
    time_slot = models.CharField(max_length=50)
    jitsi_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Meeting with {self.employee.username} on {self.date}"
class AssetAuditLog(models.Model):
    asset_id = models.IntegerField(null=True, blank=True)
    asset_tag = models.CharField(max_length=100)
    action = models.CharField(max_length=100)
    performed_by = models.CharField(max_length=200)
    date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"[{self.date}] {self.action} on {self.asset_tag}"


class RescheduleRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    resignation = models.ForeignKey(Resignation, on_delete=models.CASCADE, related_name='reschedule_requests')
    current_schedule = models.CharField(max_length=200)
    requested_date = models.DateField()
    requested_time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    rejection_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reschedule for {self.resignation.email} to {self.requested_date} {self.requested_time}"


class Notification(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    icon = models.CharField(max_length=50, default='notifications')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.email}: {self.title}"


class ExitInterview(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'DRAFT'),
        ('SUBMITTED', 'SUBMITTED'),
    ]
    employee = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name='exit_interviews')
    resignation = models.ForeignKey(Resignation, on_delete=models.CASCADE, related_name='exit_interviews')
    employee_id_code = models.CharField(max_length=50, blank=True, default='')
    employee_name = models.CharField(max_length=200, blank=True, default='')
    last_working_day = models.DateField(null=True, blank=True)
    interview_date = models.DateField(null=True, blank=True)
    exit_rating = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Questionnaire responses
    reason_for_resignation = models.TextField(blank=True, default='')
    role_satisfaction = models.IntegerField(null=True, blank=True)
    manager_relationship = models.IntegerField(null=True, blank=True)
    career_growth = models.IntegerField(null=True, blank=True)
    company_culture = models.IntegerField(null=True, blank=True)
    adequate_training = models.CharField(max_length=50, blank=True, default='')
    most_enjoyed = models.TextField(blank=True, default='')
    suggested_improvements = models.TextField(blank=True, default='')
    recommend_to_others = models.CharField(max_length=10, blank=True, default='')
    consider_rejoining = models.CharField(max_length=10, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Exit Interview for {self.employee_name} ({self.status})"


class CompanyMasterEmployee(models.Model):
    employee_id = models.IntegerField(primary_key=True)
    joining_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'company_master"."employees'
        verbose_name = "Company Master Employee"
        verbose_name_plural = "Company Master Employees"

    def __str__(self):
        return f"EMP-{self.employee_id}: {self.joining_date}"


class HRManagementStaffProfile(models.Model):
    employee_id = models.IntegerField(primary_key=True)
    date_of_joining = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'hr_management"."staff_profiles'
        verbose_name = "HR Staff Profile"
        verbose_name_plural = "HR Staff Profiles"

    def __str__(self):
        return f"EMP-{self.employee_id}: {self.date_of_joining}"


class UserDirectoryEmployeePersonal(models.Model):
    employee_id = models.IntegerField(primary_key=True)
    hire_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'user_directory"."employee_personal'
        verbose_name = "Employee Personal Profile"
        verbose_name_plural = "Employee Personal Profiles"

    def __str__(self):
        return f"EMP-{self.employee_id}: {self.hire_date}"


class JoiningDateAuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    employee_id = models.IntegerField()
    action_type = models.CharField(max_length=100)
    previous_value = models.DateField(null=True, blank=True)
    new_value = models.DateField(null=True, blank=True)
    actor = models.CharField(max_length=200, default='System')
    sync_status = models.JSONField(default=dict)

    def __str__(self):
        return f"EMP-{self.employee_id} updated to {self.new_value} by {self.actor}"


class SyncQueue(models.Model):
    employee_id = models.IntegerField()
    portal = models.CharField(max_length=50) # 'hr' or 'employee'
    date_val = models.DateField()
    retries = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='Pending') # Pending, Failed, Success
    last_attempt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Sync {self.portal} for EMP-{self.employee_id} -> {self.date_val} ({self.status})"




