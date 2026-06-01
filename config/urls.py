from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from appointments.views import stripe_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/doctors/', include('doctors.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/payment/webhook/', csrf_exempt(stripe_webhook), name='stripe-webhook'),
]
