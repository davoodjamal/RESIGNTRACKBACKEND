from django.contrib import admin
from .models import AppUser, Resignation, SystemSettings, AuditLog

@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role')
    search_fields = ('username', 'email')

@admin.register(Resignation)
class ResignationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'status', 'submission_date', 'relieving_date')
    list_filter = ('status', 'submission_date')
    search_fields = ('name', 'email')

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('notice_period', 'auto_approve')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('time', 'message')
    search_fields = ('message',)

