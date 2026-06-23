from django.urls import path
from ..views import (
    ResignationUpdateView,
    settings_view,
    AuditLogListCreateView,
    AssetListCreateView,
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



