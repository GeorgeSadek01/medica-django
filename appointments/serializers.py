from rest_framework import serializers
from .models import Appointment
from doctors.models import AvailabilityBlock


ALLOWED_TRANSITIONS = {
    Appointment.Status.PENDING: [Appointment.Status.CONFIRMED, Appointment.Status.CANCELLED],
    Appointment.Status.CONFIRMED: [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED],
    Appointment.Status.CANCELLED: [],
    Appointment.Status.COMPLETED: [],
}


class AppointmentSerializer(serializers.ModelSerializer):
    time = serializers.TimeField(format='%H:%M')
    allowed_next_statuses = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'doctor_name', 'specialty', 'patient',
            'patient_name', 'date', 'time_slot', 'time',
            'status', 'notes', 'doctor_notes', 'paid',
            'stripe_payment_intent_id', 'refunded', 'created_at',
            'allowed_next_statuses',
        ]
        read_only_fields = ['id', 'patient', 'doctor_name', 'specialty', 'patient_name', 'status', 'allowed_next_statuses', 'stripe_payment_intent_id', 'refunded']

    def get_allowed_next_statuses(self, obj):
        return ALLOWED_TRANSITIONS.get(obj.status, [])

    def validate_date(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError('Date must be today or in the future')
        return value

    def validate(self, data):
        from datetime import datetime, timedelta
        doctor = data.get('doctor')
        date_val = data.get('date')
        time = data.get('time')

        if doctor and date_val and time:
            day_name = date_val.strftime('%A')

            matching_block = AvailabilityBlock.objects.filter(
                doctor=doctor,
                day=day_name,
                start_time__lte=time,
                end_time__gte=time
            ).first()

            if not matching_block:
                raise serializers.ValidationError(
                    f"Doctor is not available at this time on ({day_name})"
                )

            duration = doctor.session_duration
            time_end = (datetime.combine(date_val, time) + timedelta(minutes=duration)).time()
            if time_end > matching_block.end_time:
                raise serializers.ValidationError(
                    f"The appointment end time ({time_end.strftime('%H:%M')}) exceeds the available hours"
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
        from datetime import datetime, timedelta
        doctor = attrs.get('doctor')
        date_val = attrs.get('date')
        time = attrs.get('time')

        if date_val and doctor and time:
            day_name = date_val.strftime('%A')
            blocks = AvailabilityBlock.objects.filter(doctor=doctor, day=day_name)
            if not blocks.exists():
                raise serializers.ValidationError('The doctor has no availability on this day')

            matching_block = blocks.filter(start_time__lte=time, end_time__gte=time).first()
            if not matching_block:
                raise serializers.ValidationError("The requested time is outside the doctor's available hours")

            duration = doctor.session_duration
            time_end = (datetime.combine(date_val, time) + timedelta(minutes=duration)).time()
            if time_end > matching_block.end_time:
                raise serializers.ValidationError(
                    f"The appointment end time ({time_end.strftime('%H:%M')}) exceeds the available hours"
                )

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
