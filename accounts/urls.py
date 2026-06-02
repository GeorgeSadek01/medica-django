from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='auth-register'),
    path('token/', views.token, name='auth-token'),
    path('token/refresh/', views.token_refresh, name='auth-token-refresh'),
    path('logout/', views.logout, name='auth-logout'),
    path('me/', views.me, name='auth-me'),
    path('password-reset/', views.password_reset, name='auth-password-reset'),
    path('password-reset/confirm/', views.password_reset_confirm, name='auth-password-reset-confirm'),
    path('verify-email/', views.verify_email, name='auth-verify-email'),
    path('resend-verification/', views.resend_verification, name='auth-resend-verification'),
    path('google/', views.google_login, name='auth-google'),
]
