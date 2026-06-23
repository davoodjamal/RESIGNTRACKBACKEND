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
]
