from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorAppointmentViewSet
from . import views

router = DefaultRouter()
router.register(r'doctor-appointments', DoctorAppointmentViewSet, basename='doctor-appointments')

urlpatterns = [
    path('', include(router.urls)),
    path('appointments/', views.appointment_list, name='appointment-list'),
    path('appointments/<int:pk>/', views.appointment_detail, name='appointment-detail'),
]
