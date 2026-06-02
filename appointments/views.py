from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Appointment
from .serializers import AppointmentSerializer

from doctors.views import IsDoctorUser

class DoctorAppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsDoctorUser]

    def get_queryset(self):
        return Appointment.objects.filter(doctor=self.request.user.doctor_profile)

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def appointment_list(request):
    user = request.user

    if user.role == 'admin':
        appointments = Appointment.objects.all()

    elif user.role == 'doctor':
        appointments = Appointment.objects.filter(doctor__user=user)

    else:
        appointments = Appointment.objects.filter(patient=user)

    status_filter = request.query_params.get('status')
    specialty = request.query_params.get('specialty')
    search = request.query_params.get('search')
    doctor = request.query_params.get('doctor')
    patient = request.query_params.get('patient')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if specialty:
        appointments = appointments.filter(specialty__icontains=specialty)
    if search:
        appointments = appointments.filter(
            Q(doctor_name__icontains=search) |
            Q(patient_name__icontains=search)
        )
    if doctor:
        appointments = appointments.filter(doctor=doctor)
    if patient:
        appointments = appointments.filter(patient=patient)
    if date_from:
        appointments = appointments.filter(date__gte=date_from)
    if date_to:
        appointments = appointments.filter(date__lte=date_to)

    serializer = AppointmentSerializer(appointments, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def appointment_detail(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        return Response(
            {'error': 'Appointment not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    user = request.user

    is_admin = user.role == 'admin'
    is_doctor = user.role == 'doctor' and appointment.doctor.user.id == user.id
    is_patient = user.role == 'patient' and appointment.patient.id == user.id

    if not (is_admin or is_doctor or is_patient):
        return Response(
            {'error': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == 'GET':
        return Response(AppointmentSerializer(appointment).data)

    if request.method == 'PATCH':
        serializer = AppointmentSerializer(
            appointment,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not is_admin:
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        appointment_id = appointment.id
        appointment.delete()
        return Response({'deleted': True, 'id': appointment_id})
