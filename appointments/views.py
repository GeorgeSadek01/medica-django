import logging
from datetime import datetime, timedelta

import stripe
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse

from accounts.email_service import EmailService
from .models import Appointment
from .serializers import (
    AppointmentSerializer, AppointmentCreateSerializer, AppointmentUpdateSerializer,
    ALLOWED_TRANSITIONS,
)

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


def process_refund(appointment):
    if not appointment.paid or not appointment.stripe_payment_intent_id:
        return False
    try:
        stripe.Refund.create(payment_intent=appointment.stripe_payment_intent_id)
        appointment.paid = False
        appointment.refunded = True
        appointment.save(update_fields=['paid', 'refunded'])
        return True
    except stripe.error.StripeError:
        return False


def can_cancel(appointment):
    appointment_dt = datetime.combine(appointment.date, appointment.time)
    return datetime.now() < appointment_dt - timedelta(hours=24)


def validate_transition(appointment, new_status):
    if new_status and new_status != appointment.status:
        allowed = ALLOWED_TRANSITIONS.get(appointment.status, [])
        if new_status not in allowed:
            return False, f"Cannot transition from '{appointment.status}' to '{new_status}'."
    return True, None


def can_user_set_status(user, appointment, new_status):
    if user.role == 'admin':
        return True, None
    if new_status == Appointment.Status.CANCELLED:
        if appointment.patient == user:
            allowed = ALLOWED_TRANSITIONS.get(appointment.status, [])
            if Appointment.Status.CANCELLED not in allowed:
                return False, "You can no longer cancel this appointment."
            if not can_cancel(appointment):
                return False, "Cancellation is only allowed at least 24 hours before the appointment."
            return True, None
        if user.role == 'doctor':
            return True, None
        return False, "Not authorized to cancel this appointment."
    if new_status in [Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED]:
        if user.role == 'doctor':
            return True, None
        return False, "Only doctors can confirm or complete appointments."
    return True, None


class DoctorAppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            return Appointment.objects.filter(doctor=self.request.user.doctor_profile)
        except AttributeError:
            return Appointment.objects.none()

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_appointment(self, request, pk=None):
        appointment = self.get_object()
        ok, err = validate_transition(appointment, Appointment.Status.CONFIRMED)
        if not ok:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save()
        try:
            EmailService.send_appointment_confirmed(appointment)
        except Exception:
            logger.exception("Failed to send confirmation email for appointment %s", appointment.id)
        serializer = self.get_serializer(appointment)
        return Response({"message": "Appointment confirmed successfully", "appointment": serializer.data})

    @action(detail=True, methods=['post'], url_path='reject')
    def reject_appointment(self, request, pk=None):
        appointment = self.get_object()
        ok, err = validate_transition(appointment, Appointment.Status.CANCELLED)
        if not ok:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
        refund_issued = False
        if appointment.paid and appointment.stripe_payment_intent_id:
            refund_issued = process_refund(appointment)
            if not refund_issued:
                return Response({'error': 'Failed to process refund. Please try again or contact support.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()
        try:
            EmailService.send_appointment_cancelled(appointment, cancelled_by_role='doctor')
        except Exception:
            logger.exception("Failed to send cancellation email for appointment %s", appointment.id)
        serializer = self.get_serializer(appointment)
        msg = "Appointment cancelled successfully"
        if refund_issued:
            msg += " and refund has been issued."
        return Response({"message": msg, "appointment": serializer.data})

    @action(detail=True, methods=['post'], url_path='add-notes')
    def add_doctor_notes(self, request, pk=None):
        appointment = self.get_object()
        notes = request.data.get('doctor_notes', '')
        appointment.doctor_notes = notes
        was_completed = False
        if appointment.status == Appointment.Status.CONFIRMED:
            ok, err = validate_transition(appointment, Appointment.Status.COMPLETED)
            if ok:
                appointment.status = Appointment.Status.COMPLETED
                was_completed = True
        appointment.save()
        if was_completed:
            try:
                EmailService.send_appointment_completed(appointment)
            except Exception:
                logger.exception("Failed to send completion email for appointment %s", appointment.id)
        serializer = self.get_serializer(appointment)
        msg = "Doctor notes saved."
        if appointment.status == Appointment.Status.COMPLETED:
            msg = "Doctor notes saved and appointment marked as completed."
        return Response({
            "message": msg,
            "appointment": serializer.data
        })


class PatientAppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(patient=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        doctor_profile = serializer.validated_data['doctor']
        serializer.save(
            patient=user,
            patient_name=f"{user.first_name} {user.last_name}".strip() or user.username,
            doctor_name=f"{doctor_profile.first_name} {doctor_profile.last_name}",
            specialty=doctor_profile.specialty,
            status=Appointment.Status.PENDING
        )


class AppointmentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def appointment_list_create(request):
    if request.method == 'GET':
        user = request.user
        if user.role == 'admin':
            queryset = Appointment.objects.all()
        elif user.role == 'doctor':
            try:
                doctor = user.doctor_profile
                queryset = Appointment.objects.filter(doctor=doctor)
            except AttributeError:
                queryset = Appointment.objects.none()
        else:
            queryset = Appointment.objects.filter(patient=user)

        status_filter = request.query_params.get('status')
        specialty = request.query_params.get('specialty')
        search = request.query_params.get('search')
        doctor_id = request.query_params.get('doctor')
        patient_id = request.query_params.get('patient')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if specialty:
            queryset = queryset.filter(specialty__icontains=specialty)
        if search:
            queryset = queryset.filter(
                Q(doctor_name__icontains=search) | Q(patient_name__icontains=search)
            )
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        queryset = queryset.order_by('-date', '-time')
        paginator = AppointmentPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AppointmentSerializer(queryset, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if request.user.role not in ['patient', 'admin']:
            return Response({'error': 'Only patients can book appointments'}, status=status.HTTP_403_FORBIDDEN)

        serializer = AppointmentCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({'error': 'Validation failed', 'field_errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        doctor = serializer.validated_data['doctor']
        if not doctor.user.verified:
            return Response({'error': 'This doctor is not yet verified and cannot accept appointments'}, status=status.HTTP_403_FORBIDDEN)
        date = serializer.validated_data['date']
        time_slot = serializer.validated_data['time_slot']

        if request.user.role == 'patient':
            conflict = Appointment.objects.filter(
                patient=request.user,
                doctor=doctor,
                date=date,
                status__in=['confirmed', 'completed'],
            ).exists()
            if conflict:
                return Response(
                    {'error': 'You already have an appointment with this doctor on this day'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            slot = Appointment.objects.select_for_update().filter(
                doctor=doctor,
                date=date,
                time_slot=time_slot,
                status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
            ).first()
            if slot:
                return Response(
                    {'error': 'This time slot is already booked'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            appointment = serializer.save()
        out_serializer = AppointmentSerializer(appointment)

        try:
            checkout_session = stripe.checkout.Session.create(
                mode='payment',
                line_items=[{
                    'price_data': {
                        'currency': 'egp',
                        'product_data': {
                            'name': f'Appointment with Dr. {appointment.doctor_name}',
                            'description': f'{appointment.specialty} - {appointment.date} at {appointment.time}',
                        },
                        'unit_amount': appointment.doctor.session_price * 100,
                    },
                    'quantity': 1,
                }],
                client_reference_id=str(appointment.id),
                metadata={'appointment_id': appointment.id},
                success_url=settings.STRIPE_SUCCESS_URL.format(id=appointment.id),
                cancel_url=settings.STRIPE_CANCEL_URL.format(id=appointment.id),
            )
            payment_url = checkout_session.url
            session_id = checkout_session.id
        except Exception:
            payment_url = None
            session_id = None

        data = out_serializer.data
        data['payment_url'] = payment_url
        data['session_id'] = session_id
        return Response(data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def appointment_detail_view(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    is_authorized = (
        user.role == 'admin' or
        appointment.patient == user or
        (user.role == 'doctor' and hasattr(user, 'doctor_profile') and user.doctor_profile == appointment.doctor)
    )
    if not is_authorized:
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = AppointmentSerializer(appointment)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        if 'paid' in request.data and request.user.role != 'admin':
            return Response({'error': 'Only admins can set paid directly.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = AppointmentUpdateSerializer(appointment, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': 'Validation failed', 'field_errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        status_value = serializer.validated_data.get('status')

        if status_value:
            ok, err = validate_transition(appointment, status_value)
            if not ok:
                return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
            ok, err = can_user_set_status(user, appointment, status_value)
            if not ok:
                return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

            if status_value == Appointment.Status.CANCELLED and appointment.paid and appointment.stripe_payment_intent_id:
                if user.role in ['doctor', 'admin', 'patient']:
                    refund_ok = process_refund(appointment)
                    if not refund_ok:
                        return Response({'error': 'Failed to process refund. Please try again or contact support.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    return Response({'error': 'Cannot cancel a paid appointment. Please contact support.'}, status=status.HTTP_403_FORBIDDEN)

        if 'date' in serializer.validated_data or 'time_slot' in serializer.validated_data:
            doctor = appointment.doctor
            date_val = serializer.validated_data.get('date', appointment.date)
            slot_val = serializer.validated_data.get('time_slot', appointment.time_slot)
            slot_taken = Appointment.objects.filter(
                doctor=doctor, date=date_val, time_slot=slot_val,
                status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
            ).exclude(pk=appointment.pk).exists()
            if slot_taken:
                return Response({'error': 'This time slot is already booked'}, status=status.HTTP_400_BAD_REQUEST)

        old_status = appointment.status
        appointment = serializer.save()
        if status_value == Appointment.Status.CANCELLED and old_status != Appointment.Status.CANCELLED:
            try:
                cancelled_by = 'patient' if user.role == 'patient' else user.role
                EmailService.send_appointment_cancelled(appointment, cancelled_by_role=cancelled_by)
            except Exception:
                logger.exception("Failed to send cancellation email for appointment %s", appointment.id)
        out_serializer = AppointmentSerializer(appointment)
        return Response(out_serializer.data)

    elif request.method == 'DELETE':
        if request.user.role != 'admin':
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        appointment.delete()
        return Response({'deleted': True, 'id': pk})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_session(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

    if appointment.patient != request.user:
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    if appointment.paid:
        return Response({'error': 'Appointment is already paid'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        checkout_session = stripe.checkout.Session.create(
            mode='payment',
            line_items=[{
                'price_data': {
                    'currency': 'egp',
                    'product_data': {
                        'name': f'Appointment with Dr. {appointment.doctor_name}',
                        'description': f'{appointment.specialty} - {appointment.date} at {appointment.time}',
                    },
                    'unit_amount': appointment.doctor.session_price * 100,
                },
                'quantity': 1,
            }],
            client_reference_id=str(appointment.id),
            metadata={'appointment_id': appointment.id},
            success_url=settings.STRIPE_SUCCESS_URL.format(id=appointment.id),
            cancel_url=settings.STRIPE_CANCEL_URL.format(id=appointment.id),
        )
        return Response({'payment_url': checkout_session.url, 'session_id': checkout_session.id})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_payment(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

    if appointment.patient != request.user:
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    if appointment.paid:
        return Response({'error': 'Already paid'}, status=status.HTTP_400_BAD_REQUEST)

    session_id = request.data.get('session_id')
    if not session_id:
        return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status != 'paid':
            return Response({'error': 'Payment not completed'}, status=status.HTTP_400_BAD_REQUEST)
        if str(appointment.id) != session.metadata.appointment_id:
            return Response({'error': 'Session does not match this appointment'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Invalid session: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    appointment.stripe_payment_intent_id = session.get('payment_intent', '')
    appointment.status = Appointment.Status.CONFIRMED
    appointment.paid = True
    appointment.save()

    try:
        EmailService.send_payment_confirmation(appointment)
        EmailService.send_appointment_confirmed(appointment)
    except Exception:
        logger.exception("Failed to send payment confirmation email for appointment %s", appointment.id)

    return Response(AppointmentSerializer(appointment).data)


def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        appointment_id = session.get('metadata', {}).get('appointment_id')
        if appointment_id:
            try:
                appointment = Appointment.objects.get(pk=appointment_id)
                appointment.stripe_payment_intent_id = session.get('payment_intent', '')
                appointment.status = Appointment.Status.CONFIRMED
                appointment.paid = True
                appointment.save()
                try:
                    EmailService.send_payment_confirmation(appointment)
                    EmailService.send_appointment_confirmed(appointment)
                except Exception:
                    logger.exception("Failed to send payment confirmation email for appointment %s", appointment.id)
            except Appointment.DoesNotExist:
                pass

    return HttpResponse(status=200)
