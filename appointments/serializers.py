from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'doctor_name', 'specialty',
            'patient', 'patient_name', 'date', 'time_slot',
            'time', 'status', 'notes', 'doctor_notes', 'paid',
        ]
        read_only_fields = ['id', 'doctor_name', 'specialty', 'patient_name']