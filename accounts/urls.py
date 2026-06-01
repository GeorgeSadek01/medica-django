from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='auth-register'),
    path('token/', views.token, name='auth-token'),
    path('token/refresh/', views.token_refresh, name='auth-token-refresh'),
    path('logout/', views.logout, name='auth-logout'),
    path('me/', views.me, name='auth-me'),
]
