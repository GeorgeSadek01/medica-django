from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import DoctorAppointmentViewSet
from . import views

router = SimpleRouter()
router.register(r'doctor-appointments', DoctorAppointmentViewSet, basename='doctor-appointments')

urlpatterns = [
    path('', include(router.urls)),
    path('', views.appointment_list_create, name='appointment-list-create'),
    path('<int:pk>/', views.appointment_detail_view, name='appointment-detail'),
    path('<int:pk>/payment/', views.create_payment_session, name='appointment-payment'),
    path('<int:pk>/confirm-payment/', views.confirm_payment, name='appointment-confirm-payment'),
]
