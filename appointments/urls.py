from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorAppointmentViewSet

router = DefaultRouter()
router.register(r'doctor-appointments', DoctorAppointmentViewSet, basename='doctor-appointments')

urlpatterns = [
    path('', include(router.urls)),
]