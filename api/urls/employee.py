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
    EmployeeDetailView,
)

urlpatterns = [
    path('resignations/', ResignationListCreateView.as_view(), name='resignation-list'),
    path('resignations/draft/', ResignationDraftView.as_view(), name='resignation-draft'),
    path('resignations/draft/<int:pk>/', ResignationDraftUpdateView.as_view(), name='resignation-draft-update'),
    path('resignations/submit/', ResignationSubmitView.as_view(), name='resignation-submit'),
    path('resignations/status/', EmployeeResignationStatusView.as_view(), name='resignation-status'),
    path('resignations/<int:pk>/', ResignationDetailView.as_view(), name='resignation-detail'),
    path('resignations/<int:pk>/withdraw/', ResignationWithdrawView.as_view(), name='resignation-withdraw'),
    path('resignations/<int:pk>/feedback/', ResignationFeedbackView.as_view(), name='resignation-feedback'),
    path('dashboard/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
]
