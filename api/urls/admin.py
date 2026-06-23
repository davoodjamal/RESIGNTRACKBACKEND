from django.urls import path
from ..views import (
    UserListView,
    UserDetailView,
    DashboardMetricsView,
    SystemHealthView,
    SystemHealthV1View,
    AdminAnalyticsSyncView,
    AdminAuditLogListView,
    admin_audit_logs_stream,
    AnalyticsPendingApprovalsView,
    AnalyticsFailedLoginsView,
    AnalyticsHourlyActivityView,
    SystemUsageSnapshotView,
    system_usage_stream,
)

urlpatterns = [
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('dashboard/metrics/', DashboardMetricsView.as_view(), name='dashboard-metrics'),
    path('system/health/', SystemHealthView.as_view(), name='system-health'),
    path('v1/system-health/', SystemHealthV1View.as_view(), name='system-health-v1'),
    path('v1/admin/analytics/sync/', AdminAnalyticsSyncView.as_view(), name='admin-analytics-sync'),
    path('v1/admin/audit-logs/', AdminAuditLogListView.as_view(), name='admin-audit-logs'),
    path('v1/admin/audit-logs/stream/', admin_audit_logs_stream, name='admin-audit-logs-stream'),
    path('analytics/approvals/pending/', AnalyticsPendingApprovalsView.as_view(), name='analytics-approvals-pending'),
    path('analytics/logins/failed/', AnalyticsFailedLoginsView.as_view(), name='analytics-logins-failed'),
    path('analytics/activity/hourly/', AnalyticsHourlyActivityView.as_view(), name='analytics-hourly-activity'),
    path('v1/admin/analytics/system-usage/snapshot/', SystemUsageSnapshotView.as_view(), name='system-usage-snapshot'),
    path('v1/admin/analytics/system-usage/stream/', system_usage_stream, name='system-usage-stream'),
]
