from django.urls import path
from . import views

urlpatterns = [
    path('specialties/', views.specialty_list, name='specialty-list'),
    path('specialties/<int:pk>/', views.specialty_detail, name='specialty-detail'),
]