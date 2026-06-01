from django.urls import path
from . import views

urlpatterns = [
    path('', views.appointment_list, name='appointment-list'),
    path('<int:pk>/', views.appointment_detail, name='appointment-detail'),
    path('create/', views.appointment_create, name='appointment-create'),
    path('<int:pk>/update/', views.appointment_update, name='appointment-update'),
    path('<int:pk>/delete/', views.appointment_delete, name='appointment-delete'),
    path('<int:pk>/payment/', views.create_payment_session, name='appointment-payment'),
    path('<int:pk>/confirm-payment/', views.confirm_payment, name='appointment-confirm-payment'),
]
