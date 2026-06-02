from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import DoctorProfileViewSet, AvailabilityViewSet
from . import views

router = SimpleRouter()
router.register(r'profile', DoctorProfileViewSet, basename='doctor-profile')
router.register(r'availability', AvailabilityViewSet, basename='doctor-availability')

urlpatterns = [
    path('', include(router.urls)),
    path('', views.doctor_list, name='doctor-list'),
    path('<int:pk>/', views.doctor_detail, name='doctor-detail'),
    path('<int:pk>/availability/', views.doctor_availability, name='doctor-availability'),
    path('<int:pk>/availability/<int:slot_id>/', views.doctor_availability, name='doctor-availability-slot'),
    path('documents/upload/', views.upload_documents, name='doctor-document-upload'),
    path('documents/', views.document_list, name='doctor-document-list'),
    path('documents/<int:pk>/review/', views.review_document, name='doctor-document-review'),
]
