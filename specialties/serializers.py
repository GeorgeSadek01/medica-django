from rest_framework import serializers
from .models import Specialty


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ['id', 'name']

    def validate_name(self, value):
        if Specialty.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError('Specialty with this name already exists.')
        return value