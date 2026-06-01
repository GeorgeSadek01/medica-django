from rest_framework import serializers
from .models import Appointment
from doctors.models import AvailabilityBlock
import datetime

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'doctor_name', 'specialty', 'patient', 
            'patient_name', 'date', 'time_slot', 'time', 
            'status', 'notes', 'doctor_notes', 'paid', 'created_at'
        ]
        read_only_fields = ['patient', 'doctor_name', 'specialty', 'patient_name', 'status']

    def validate(self, data):
        doctor = data['doctor']
        date = data['date']
        time = data['time']

        day_name = date.strftime('%A')

        is_available = AvailabilityBlock.objects.filter(
            doctor=doctor,
            day=day_name,
            start_time__lte=time,
            end_time__gte=time
        ).exists()

        if not is_available:
            raise serializers.ValidationError(
                f"Doctor does not available at this time on ({day_name})"
            )
        
        is_booked = Appointment.objects.filter(
            doctor=doctor,
            date=date,
            time=time,
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
        ).exists()

        if is_booked:
            raise serializers.ValidationError(
                "This date is already booked by another patient plz select another"
            )
            
        return data