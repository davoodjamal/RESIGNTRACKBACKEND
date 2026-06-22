from django.urls import path
from ..views import (
    ResignationUpdateView,
    settings_view,
    AuditLogListCreateView,
)

urlpatterns = [
    path('resignations/<int:pk>/', ResignationUpdateView.as_view(), name='resignation-update'),
    path('settings/', settings_view, name='settings'),
    path('audit-logs/', AuditLogListCreateView.as_view(), name='audit-log-list'),
]
