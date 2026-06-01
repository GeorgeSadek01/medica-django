from rest_framework import serializers
from .models import DoctorProfile, AvailabilityBlock


class DoctorProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = DoctorProfile
        fields = ['user', 'username', 'email', 'first_name', 'last_name', 'specialty', 'bio', 'contact', 'session_price']
        read_only_fields = ['user']

class AvailabilityBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityBlock
        fields = ['id', 'doctor', 'day', 'start_time', 'end_time']
        read_only_fields = ['doctor']
    
    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("Start time must be before end time.")
        return data

