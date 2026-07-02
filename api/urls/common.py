from django.urls import path
from ..views import login_view, health_check, UserProfileView

urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('login/', login_view, name='login'),
    path('users/me/', UserProfileView.as_view(), name='user-profile'),
]
