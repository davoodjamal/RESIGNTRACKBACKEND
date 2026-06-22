from django.urls import path, include

urlpatterns = [
    path('', include('api.urls.common')),
    path('', include('api.urls.admin')),
    path('', include('api.urls.employee')),
    path('', include('api.urls.hr')),
]
