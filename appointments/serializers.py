from rest_framework import serializers
from .models import Appointment
from doctors.models import AvailabilityBlock


class AppointmentSerializer(serializers.ModelSerializer):
    time = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'doctor_name', 'specialty', 'patient',
            'patient_name', 'date', 'time_slot', 'time',
            'status', 'notes', 'doctor_notes', 'paid', 'created_at'
        ]
        read_only_fields = ['id', 'patient', 'doctor_name', 'specialty', 'patient_name', 'status']

    def validate_date(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError('Date must be today or in the future')
        return value

    def validate(self, data):
        doctor = data.get('doctor')
        date_val = data.get('date')
        time = data.get('time')

        if doctor and date_val and time:
            day_name = date_val.strftime('%A')

            is_available = AvailabilityBlock.objects.filter(
                doctor=doctor,
                day=day_name,
                start_time__lte=time,
                end_time__gte=time
            ).exists()

            if not is_available:
                raise serializers.ValidationError(
                    f"Doctor is not available at this time on ({day_name})"
                )

            is_booked = Appointment.objects.filter(
                doctor=doctor,
                date=date_val,
                time=time,
                status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
            ).exists()

            if is_booked:
                raise serializers.ValidationError(
                    "This time slot is already booked"
                )

        return data


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['doctor', 'date', 'time_slot', 'time', 'notes']

    def validate_date(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError('Date must be today or in the future')
        return value

    def validate(self, attrs):
        doctor = attrs.get('doctor')
        date_val = attrs.get('date')
        time = attrs.get('time')

        if date_val and doctor and time:
            day_name = date_val.strftime('%A')
            blocks = AvailabilityBlock.objects.filter(doctor=doctor, day=day_name)
            if not blocks.exists():
                raise serializers.ValidationError('The doctor has no availability on this day')
            if not blocks.filter(start_time__lte=time, end_time__gte=time).exists():
                raise serializers.ValidationError("The requested time is outside the doctor's available hours")

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        doctor = validated_data['doctor']

        validated_data['patient'] = user
        validated_data['patient_name'] = f'{user.first_name} {user.last_name}'
        validated_data['doctor_name'] = f'{doctor.first_name} {doctor.last_name}'
        validated_data['specialty'] = doctor.specialty

        return super().create(validated_data)


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['status', 'doctor_notes', 'date', 'time_slot', 'time', 'paid']

    def validate_date(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError('Date must be today or in the future')
        return value
