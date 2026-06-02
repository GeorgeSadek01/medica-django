import stripe
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse

from .models import Appointment
from .serializers import AppointmentSerializer, AppointmentCreateSerializer, AppointmentUpdateSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY


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
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save()

        serializer = self.get_serializer(appointment)
        return Response({"message": "Appointment confirmed successfully", "appointment": serializer.data})

    @action(detail=True, methods=['post'], url_path='reject')
    def reject_appointment(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()

        serializer = self.get_serializer(appointment)
        return Response({"message": "Appointment cancelled successfully", "appointment": serializer.data})

    @action(detail=True, methods=['post'], url_path='add-notes')
    def add_doctor_notes(self, request, pk=None):
        appointment = self.get_object()

        notes = request.data.get('doctor_notes', '')
        appointment.doctor_notes = notes

        appointment.status = Appointment.Status.COMPLETED
        appointment.save()

        serializer = self.get_serializer(appointment)
        return Response({
            "message": "Doctor notes added and appointment marked as completed",
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
            doctor_name=f"Dr. {doctor_profile.first_name} {doctor_profile.last_name}",
            specialty=doctor_profile.specialty,
            status=Appointment.Status.PENDING
        )


# ===== Function-based views for appointments =====

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def appointment_list(request):
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

    try:
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
    except (ValueError, TypeError):
        page = 1
        page_size = 20
    page = max(page, 1)
    page_size = max(page_size, 1)
    start = (page - 1) * page_size
    end = start + page_size
    queryset = queryset.order_by('-date', '-time')[start:end]

    serializer = AppointmentSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def appointment_detail(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if user.role != 'admin' and appointment.patient != user:
        try:
            if user.role == 'doctor' and user.doctor_profile != appointment.doctor:
                return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        except AttributeError:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    serializer = AppointmentSerializer(appointment)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def appointment_create(request):
    if request.user.role not in ['patient', 'admin']:
        return Response({'error': 'Only patients can book appointments'}, status=status.HTTP_403_FORBIDDEN)

    serializer = AppointmentCreateSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    doctor = serializer.validated_data['doctor']
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
        ).exclude(status='cancelled').first()
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


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def appointment_update(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if user.role != 'admin' and appointment.patient != user:
        try:
            if user.role == 'doctor' and user.doctor_profile != appointment.doctor:
                return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        except AttributeError:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    request.data.pop('paid', None)

    serializer = AppointmentUpdateSerializer(appointment, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    status_value = serializer.validated_data.get('status')

    if status_value == 'confirmed':
        serializer.validated_data['paid'] = True

    if status_value == 'pending' and ('date' in serializer.validated_data or 'time_slot' in serializer.validated_data):
        doctor = appointment.doctor
        date_val = serializer.validated_data.get('date', appointment.date)
        slot_val = serializer.validated_data.get('time_slot', appointment.time_slot)
        slot_taken = Appointment.objects.filter(
            doctor=doctor, date=date_val, time_slot=slot_val,
        ).exclude(pk=appointment.pk).exclude(status='cancelled').exists()
        if slot_taken:
            return Response({'error': 'This time slot is already booked'}, status=status.HTTP_400_BAD_REQUEST)

    appointment = serializer.save()
    out_serializer = AppointmentSerializer(appointment)
    return Response(out_serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def appointment_delete(request, pk):
    if request.user.role != 'admin':
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
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

    appointment.status = Appointment.Status.CONFIRMED
    appointment.paid = True
    appointment.save()

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
                appointment.status = Appointment.Status.CONFIRMED
                appointment.paid = True
                appointment.save()
            except Appointment.DoesNotExist:
                pass

    return HttpResponse(status=200)
