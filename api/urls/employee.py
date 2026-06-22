from django.urls import path
from ..views import (
    ResignationListCreateView,
    ResignationWithdrawView,
    ResignationFeedbackView,
)

urlpatterns = [
    path('resignations/', ResignationListCreateView.as_view(), name='resignation-list'),
    path('resignations/<int:pk>/withdraw/', ResignationWithdrawView.as_view(), name='resignation-withdraw'),
    path('resignations/<int:pk>/feedback/', ResignationFeedbackView.as_view(), name='resignation-feedback'),
]
