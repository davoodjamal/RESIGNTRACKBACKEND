from django.urls import path
from ..views import (
    ResignationListCreateView,
    ResignationWithdrawView,
    ResignationFeedbackView,
    ResignationDraftView,
    ResignationDraftUpdateView,
    ResignationSubmitView,
    ResignationDetailView,
    DashboardSummaryView,
    EmployeeResignationStatusView,
    NoticePeriodView,
    ExitChecklistTaskListView,
    ExitChecklistTaskUpdateView,
    ResignationChecklistTaskListView,
)

urlpatterns = [
    path('resignations/', ResignationListCreateView.as_view(), name='resignation-list'),
    path('resignations/draft/', ResignationDraftView.as_view(), name='resignation-draft'),
    path('resignations/draft/<int:pk>/', ResignationDraftUpdateView.as_view(), name='resignation-draft-update'),
    path('resignations/submit/', ResignationSubmitView.as_view(), name='resignation-submit'),
    path('resignations/status/', EmployeeResignationStatusView.as_view(), name='resignation-status'),
    path('resignations/notice-period/', NoticePeriodView.as_view(), name='resignation-notice-period'),
    path('resignations/checklist/', ExitChecklistTaskListView.as_view(), name='checklist-task-list'),
    path('resignations/checklist/<int:pk>/', ExitChecklistTaskUpdateView.as_view(), name='checklist-task-update'),
    path('resignations/<int:resignation_pk>/checklist/', ResignationChecklistTaskListView.as_view(), name='resignation-checklist-tasks'),
    path('resignations/<int:pk>/', ResignationDetailView.as_view(), name='resignation-detail'),
    path('resignations/<int:pk>/withdraw/', ResignationWithdrawView.as_view(), name='resignation-withdraw'),
    path('resignations/<int:pk>/feedback/', ResignationFeedbackView.as_view(), name='resignation-feedback'),
    path('dashboard/', DashboardSummaryView.as_view(), name='dashboard-summary'),
]
