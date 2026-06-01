from rest_framework import serializers
from .models import DoctorProfile, AvailabilityBlock


class AvailabilityBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityBlock
        fields = ['id', 'day', 'start_time', 'end_time']

    def validate(self, attrs):
        if attrs.get('start_time') and attrs.get('end_time') and attrs['start_time'] >= attrs['end_time']:
            raise serializers.ValidationError('end_time must be after start_time')
        return attrs


class DoctorProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user_id', read_only=True)
    availability = AvailabilityBlockSerializer(many=True, read_only=True)
    bookedSlots = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = ['id', 'first_name', 'last_name', 'specialty', 'bio', 'contact', 'session_price', 'availability', 'bookedSlots']

    def get_bookedSlots(self, obj):
        from appointments.models import Appointment
        slots = {}
        for apt in obj.appointments.exclude(status='cancelled').values('date', 'time'):
            date_str = apt['date'].strftime('%Y-%m-%d')
            time_str = apt['time'].strftime('%H:%M')
            slots.setdefault(date_str, []).append(time_str)
        return slots
