from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(read_only=True)
    specialty = serializers.CharField(read_only=True)
    patient_name = serializers.CharField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'doctor_name', 'specialty',
            'patient', 'patient_name',
            'date', 'time_slot', 'time',
            'status', 'notes', 'doctor_notes', 'paid',
        ]
        read_only_fields = ['id', 'status', 'paid', 'patient', 'patient_name', 'doctor_name', 'specialty']

    def validate_date(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError('Date must be today or in the future')
        return value


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
        date = attrs.get('date')
        time_slot = attrs.get('time_slot')
        time = attrs.get('time')

        from doctors.models import AvailabilityBlock
        if date and doctor:
            day_name = date.strftime('%A')
            if not AvailabilityBlock.objects.filter(doctor=doctor, day=day_name).exists():
                raise serializers.ValidationError('The doctor has no availability on this day')

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
