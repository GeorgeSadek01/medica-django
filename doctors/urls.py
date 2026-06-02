from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorProfileViewSet, AvailabilityViewSet
from . import views

router = DefaultRouter()
router.register(r'profile', DoctorProfileViewSet, basename='doctor-profile')
router.register(r'availability', AvailabilityViewSet, basename='doctor-availability')

urlpatterns = [
    path('', include(router.urls)),
    path('', views.doctor_list, name='doctor-list'),
    path('<int:pk>/', views.doctor_detail, name='doctor-detail'),
    path('<int:pk>/availability/', views.doctor_availability, name='doctor-availability'),
]
