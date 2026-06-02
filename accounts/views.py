from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Q, Count
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from doctors.models import DoctorProfile
from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer
from specialties.models import Specialty
from .serializers import RegisterSerializer, UserSerializer, AdminUserUpdateSerializer
from .models import User

token_generator = PasswordResetTokenGenerator()


def send_verification_email(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)
    verification_url = f"{settings.FRONTEND_URL}/verify-email?uidb64={uidb64}&token={token}"
    subject = 'Verify your Medica email address'
    html = render_to_string('accounts/email_verification_email.html', {
        'user': user,
        'verification_url': verification_url,
    })
    text = strip_tags(html)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [user.email])
    msg.attach_alternative(html, 'text/html')
    msg.send()


def send_password_reset_email(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)
    reset_url = f"{settings.FRONTEND_URL}/reset-password?uidb64={uidb64}&token={token}"
    subject = 'Reset your Medica password'
    html = render_to_string('accounts/password_reset_email.html', {
        'user': user,
        'reset_url': reset_url,
    })
    text = strip_tags(html)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [user.email])
    msg.attach_alternative(html, 'text/html')
    msg.send()


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        data = serializer.errors
        if 'email' in data and any(
            'already exists' in str(e) for e in data['email']
        ):
            return Response({'error': 'An account with this email already exists'}, status=status.HTTP_409_CONFLICT)
        field_errors = {}
        for field, errors in data.items():
            field_errors[field] = errors[0] if isinstance(errors, list) else str(errors)
        if 'non_field_errors' in field_errors:
            return Response({'error': field_errors.pop('non_field_errors')}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Validation failed', 'field_errors': field_errors}, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()

    if user.role == User.Role.DOCTOR:
        specialty = request.data.get('specialty', '')
        DoctorProfile.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            specialty=specialty,
            contact=user.email,
        )
        user.verified = False
        user.save(update_fields=['verified'])

    try:
        send_verification_email(user)
    except Exception:
        pass

    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def token(request):
    email = request.data.get('email', '')
    password = request.data.get('password', '')

    user = authenticate(request, username=email, password=password)
    if not user or not user.is_active:
        return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.email_verified:
        return Response({'error': 'Please verify your email address before logging in'}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    refresh_token = request.data.get('refresh', '')
    if not refresh_token:
        return Response({'error': 'Refresh token is required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        refresh = RefreshToken(refresh_token)
        return Response({'access': str(refresh.access_token)})
    except Exception:
        return Response({'error': 'Invalid or expired refresh token'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh_token = request.data.get('refresh', '')
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
    return Response({'message': 'Logged out successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    if not request.user.email_verified:
        return Response({'error': 'Email not verified'}, status=status.HTTP_403_FORBIDDEN)
    return Response(UserSerializer(request.user).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset(request):
    email = request.data.get('email', '')
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({'message': 'If an account with this email exists, a password reset link has been sent.'})

    try:
        send_password_reset_email(user)
    except Exception:
        return Response({'error': 'Failed to send reset email. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'message': 'If an account with this email exists, a password reset link has been sent.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    uidb64 = request.data.get('uidb64', '')
    token = request.data.get('token', '')
    password = request.data.get('password', '')

    if not uidb64 or not token or not password:
        return Response({'error': 'uidb64, token, and password are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return Response({'error': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)

    if not token_generator.check_token(user, token):
        return Response({'error': 'Invalid or expired reset link'}, status=status.HTTP_400_BAD_REQUEST)

    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    try:
        validate_password(password)
    except ValidationError as e:
        return Response({'error': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save()
    return Response({'message': 'Password has been reset successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    uidb64 = request.data.get('uidb64', '')
    token = request.data.get('token', '')

    if not uidb64 or not token:
        return Response({'error': 'uidb64 and token are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return Response({'error': 'Invalid verification link'}, status=status.HTTP_400_BAD_REQUEST)

    if user.email_verified:
        return Response({'message': 'Email already verified'})

    if not token_generator.check_token(user, token):
        return Response({'error': 'Invalid or expired verification link'}, status=status.HTTP_400_BAD_REQUEST)

    user.email_verified = True
    user.save(update_fields=['email_verified'])
    return Response({'message': 'Email verified successfully'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resend_verification(request):
    user = request.user
    if user.email_verified:
        return Response({'message': 'Email already verified'})

    try:
        send_verification_email(user)
    except Exception:
        return Response({'error': 'Failed to send verification email. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'message': 'Verification email sent'})


@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    credential = request.data.get('credential', '')
    if not credential:
        return Response({'error': 'Credential is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        id_info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        return Response({'error': 'Invalid Google credential'}, status=status.HTTP_400_BAD_REQUEST)

    google_id = id_info.get('sub', '')
    email = id_info.get('email', '')
    first_name = id_info.get('given_name', '')
    last_name = id_info.get('family_name', '')

    if not email:
        return Response({'error': 'Google account has no email address'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user = User.objects.select_for_update().filter(google_id=google_id).first()
        if not user:
            user = User.objects.select_for_update().filter(email__iexact=email).first()
            if user:
                if not user.google_id:
                    user.google_id = google_id
                    user.email_verified = True
                    user.save(update_fields=['google_id', 'email_verified'])
            else:
                user = User.objects.create_user(
                    email=email,
                    first_name=first_name or email.split('@')[0],
                    last_name=last_name or '',
                    role='patient',
                    google_id=google_id,
                    email_verified=True,
                )

    if not user.is_active:
        return Response({'error': 'Account is disabled'}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    })


# ===== Admin User Management =====

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request):
    if request.user.role != 'admin':
        return Response(
            {'error': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )

    users = User.objects.all()

    search = request.query_params.get('search')
    role = request.query_params.get('role')
    is_active = request.query_params.get('is_active')
    verified = request.query_params.get('verified')

    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    if role:
        users = users.filter(role=role)

    if is_active is not None:
        if is_active.lower() not in ('true', 'false'):
            return Response({'error': 'is_active must be "true" or "false".'}, status=status.HTTP_400_BAD_REQUEST)
        users = users.filter(is_active=is_active.lower() == 'true')

    if verified is not None:
        if verified.lower() not in ('true', 'false'):
            return Response({'error': 'verified must be "true" or "false".'}, status=status.HTTP_400_BAD_REQUEST)
        users = users.filter(verified=verified.lower() == 'true')

    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        if request.user.role != 'admin':
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return Response(UserSerializer(user).data)

    if request.method == 'PATCH':
        if request.user.role != 'admin' and request.user.id != user.id:
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = AdminUserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(user).data)
        return Response({'error': 'Validation failed', 'field_errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if request.user.role != 'admin':
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if not request.data.get('soft'):
            return Response(
                {'error': 'soft must be true to delete.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.soft_delete()
        return Response({
            'id': user.id,
            'is_active': user.is_active,
            'deleted_at': user.deleted_at,
        })


# Restore user
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_restore(request, pk):
    if request.user.role != 'admin':
        return Response(
            {'error': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    user.is_active = True
    user.deleted_at = None
    user.save()
    return Response(UserSerializer(user).data)


# ===== Admin Dashboard =====

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):
    if request.user.role != 'admin':
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    total_patients = User.objects.filter(role='patient').count()
    total_doctors = User.objects.filter(role='doctor').count()
    unverified_doctors = User.objects.filter(role='doctor', verified=False).count()

    appt_counts = Appointment.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status=Appointment.Status.PENDING)),
        confirmed=Count('id', filter=Q(status=Appointment.Status.CONFIRMED)),
        completed=Count('id', filter=Q(status=Appointment.Status.COMPLETED)),
        cancelled=Count('id', filter=Q(status=Appointment.Status.CANCELLED)),
    )

    total_specialties = Specialty.objects.count()

    recent_appointments = Appointment.objects.order_by('-created_at')[:10]
    recent_data = AppointmentSerializer(recent_appointments, many=True).data

    return Response({
        'users': {
            'total': total_patients + total_doctors,
            'patients': total_patients,
            'doctors': total_doctors,
            'unverified_doctors': unverified_doctors,
        },
        'appointments': appt_counts,
        'specialties': total_specialties,
        'recent_appointments': recent_data,
    })
