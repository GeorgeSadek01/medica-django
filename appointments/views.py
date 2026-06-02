from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import Appointment
from .serializers import AppointmentSerializer


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

    # Filters
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

    # التحقق من الصلاحية
    is_admin = user.role == 'admin'
    is_doctor = user.role == 'doctor' and appointment.doctor.user.id == user.id
    is_patient = user.role == 'patient' and appointment.patient.id == user.id

    if not (is_admin or is_doctor or is_patient):
        return Response(
            {'error': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # GET
    if request.method == 'GET':
        return Response(AppointmentSerializer(appointment).data)

    # PATCH
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