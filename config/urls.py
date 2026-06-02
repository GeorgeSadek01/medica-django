import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from appointments.views import stripe_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/doctors/', include('doctors.urls')),
    path('api/', include('accounts.urls_users')),
    path('api/', include('specialties.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/payment/webhook/', csrf_exempt(stripe_webhook), name='stripe-webhook'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if not settings.DEBUG:
    frontend_index = settings.BASE_DIR / 'frontend' / 'build' / 'index.html'
    if frontend_index.exists():
        urlpatterns += [
            re_path(r'^.*$', TemplateView.as_view(
                template_name='index.html',
                extra_context={},
            )),
        ]
