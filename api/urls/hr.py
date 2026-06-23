from django.urls import path
from ..views import (
    ResignationUpdateView,
    settings_view,
    AuditLogListCreateView,
    AssetListCreateView,
    AssetRetrieveUpdateDestroyView,
    AssetAssignView,
    AssetReturnView,
    AssetMaintenanceView,
    AssetDashboardView,
    EmployeeListView,
    ExitInterviewListView,
    ExitInterviewDetailView,
    LatestExitInterviewView,
    ExitInterviewAnalyticsView,
    MeetingViewSet,
    AssetDetailView,
    AssetAssignView,
    AssetReturnView,
    AssetAuditLogListView,
    RescheduleRequestCreateView,
    RescheduleRequestListView,
    RescheduleRequestDecisionView,
    NotificationListView,
    NotificationMarkReadAllView,
    NotificationMarkReadView,
    GlobalSearchView,
)

urlpatterns = [
    path('resignations/<int:pk>/', ResignationUpdateView.as_view(), name='resignation-update'),
    path('settings/', settings_view, name='settings'),
    path('audit-logs/', AuditLogListCreateView.as_view(), name='audit-log-list'),
    path('assets/', AssetListCreateView.as_view(), name='asset-list'),
    path('assets/<int:pk>/', AssetRetrieveUpdateDestroyView.as_view(), name='asset-detail'),
    path('assets/<int:pk>/assign/', AssetAssignView.as_view(), name='asset-assign'),
    path('assets/<int:pk>/return/', AssetReturnView.as_view(), name='asset-return'),
    path('assets/<int:pk>/maintenance/', AssetMaintenanceView.as_view(), name='asset-maintenance'),
    path('assets/dashboard/', AssetDashboardView.as_view(), name='asset-dashboard'),
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    
    # Exit Interview Endpoints
    path('exit-interviews/', ExitInterviewListView.as_view(), name='exit-interview-list'),
    path('exit-interviews/latest/', LatestExitInterviewView.as_view(), name='latest-exit-interview'),
    path('exit-interviews/analytics/', ExitInterviewAnalyticsView.as_view(), name='exit-interview-analytics'),
    path('exit-interviews/<int:pk>/', ExitInterviewDetailView.as_view(), name='exit-interview-detail'),
    
    # Jitsi Meeting Endpoints
    path('meetings/', MeetingViewSet.as_view({'get': 'list', 'post': 'create'}), name='meeting-list'),
    path('meetings/<int:pk>/', MeetingViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='meeting-detail'),
    path('assets/', AssetListCreateView.as_view(), name='asset-list-create'),
    path('assets/<int:pk>/', AssetDetailView.as_view(), name='asset-detail'),
    path('assets/<int:pk>/assign/', AssetAssignView.as_view(), name='asset-assign'),
    path('assets/<int:pk>/return/', AssetReturnView.as_view(), name='asset-return'),
    path('assets/audit/', AssetAuditLogListView.as_view(), name='asset-audit-log-list'),
    path('resignations/reschedule/', RescheduleRequestCreateView.as_view(), name='reschedule-create'),
    path('resignations/reschedule/list/', RescheduleRequestListView.as_view(), name='reschedule-list'),
    path('resignations/reschedule/<int:pk>/decision/', RescheduleRequestDecisionView.as_view(), name='reschedule-decision'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/read-all/', NotificationMarkReadAllView.as_view(), name='notification-read-all'),
    path('notifications/<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-read'),
    path('search/', GlobalSearchView.as_view(), name='global-search'),
]



