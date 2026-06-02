from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    specialty = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'role', 'specialty']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists', code='conflict')
        return value

    def validate(self, attrs):
        attrs.pop('specialty', None)
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'role', 'phone', 'avatar', 'is_active',
            'verified', 'deleted_at',  # ← لازم يكون موجود
        ]
        read_only_fields = ['id', 'deleted_at']

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email',
            'phone', 'avatar', 'is_active',
            'verified', 'role',
        ]

    def validate_phone(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError('Phone must contain digits only.')
        if value and len(value) != 11:
            raise serializers.ValidationError('Phone must be 11 digits.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user.role != 'admin':
            for field in ['role', 'is_active', 'verified']:
                if field in attrs:
                    raise serializers.ValidationError(
                        {field: 'Only admins can change this field.'}
                    )
        return attrs