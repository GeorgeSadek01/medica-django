from rest_framework import serializers
from .models import DoctorProfile, AvailabilityBlock


class AvailabilityBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityBlock
        fields = ['id', 'day', 'start_time', 'end_time']

    def validate(self, attrs):
        start = attrs.get('start_time')
        end = attrs.get('end_time')
        if start and end and start >= end:
            raise serializers.ValidationError('end_time must be after start_time')
        return attrs


class DoctorProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user_id', read_only=True)
    availability = AvailabilityBlockSerializer(many=True, read_only=True)
    bookedSlots = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = ['id', 'first_name', 'last_name', 'specialty', 'bio', 'contact', 'session_price', 'availability', 'bookedSlots']

    def validate_specialty(self, value):
        from specialties.models import Specialty
        if not Specialty.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(f"Specialty '{value}' does not exist.")
        return value

    def validate_contact(self, value):
        if not value:
            raise serializers.ValidationError('Contact is required.')
        return value

    def get_bookedSlots(self, obj):
        from appointments.models import Appointment
        slots = {}
        for apt in obj.appointments.exclude(status='cancelled').values('date', 'time'):
            date_str = apt['date'].strftime('%Y-%m-%d')
            time_str = apt['time'].strftime('%H:%M')
            slots.setdefault(date_str, []).append(time_str)
        return slots
