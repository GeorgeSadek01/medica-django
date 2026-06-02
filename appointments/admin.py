from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'doctor_name', 'date', 'time', 'status', 'paid']
    list_filter = ['status', 'paid', 'specialty']
    search_fields = ['patient_name', 'doctor_name']
    ordering = ['-date']
