from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorProfileViewSet, AvailabilityViewSet

router = DefaultRouter()
router.register(r'profile', DoctorProfileViewSet, basename='doctor-profile')
router.register(r'availability', AvailabilityViewSet, basename='doctor-availability')

urlpatterns = [
    path('', include(router.urls)),
]