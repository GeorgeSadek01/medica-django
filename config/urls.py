from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/doctors/', include('doctors.urls')),
    path('api/', include('accounts.urls_users')),
    path('api/', include('specialties.urls')),
    path('api/', include('appointments.urls')),
]
