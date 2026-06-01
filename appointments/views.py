from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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



