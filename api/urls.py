from django.urls import path
from .views import (
    login_view,
    UserListView,
    UserDetailView,
    ResignationListCreateView,
    ResignationUpdateView,
    ResignationWithdrawView,
    settings_view,
    AuditLogListCreateView,
    health_check,
)

urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('login/', login_view, name='login'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('resignations/', ResignationListCreateView.as_view(), name='resignation-list'),
    path('resignations/<int:pk>/', ResignationUpdateView.as_view(), name='resignation-update'),
    path('resignations/<int:pk>/withdraw/', ResignationWithdrawView.as_view(), name='resignation-withdraw'),
    path('settings/', settings_view, name='settings'),
    path('audit-logs/', AuditLogListCreateView.as_view(), name='audit-log-list'),
]

