from django.contrib import admin
from .models import DoctorProfile, AvailabilityBlock, DoctorDocument


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'specialty', 'session_price']
    list_filter = ['specialty']
    search_fields = ['first_name', 'last_name', 'specialty']


@admin.register(AvailabilityBlock)
class AvailabilityBlockAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'day', 'start_time', 'end_time']
    list_filter = ['day']


@admin.register(DoctorDocument)
class DoctorDocumentAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'status', 'uploaded_at']
    list_filter = ['status']
