from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.response import Response
from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer

from .models import DoctorProfile, AvailabilityBlock
from .serializers import DoctorProfileSerializer, AvailabilityBlockSerializer

from rest_framework.permissions import BasePermission

class IsDoctorUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'doctor_profile')
    

class DoctorProfileViewSet(viewsets.ModelViewSet):
    queryset = DoctorProfile.objects.all()
    serializer_class = DoctorProfileSerializer
    permission_classes = [IsAuthenticated, IsDoctorUser]

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='me')
    def manage_me(self, request):
        doctor = request.user.doctor_profile
        if request.method == 'GET':
            serializer = self.get_serializer(doctor)
            return Response(serializer.data)
            
        elif request.method in ['PUT', 'PATCH']:
            serializer = self.get_serializer(doctor, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Endpoint: /api/doctors/profile/<doctor_id>/availability_slots/
    @action(detail=True, methods=['get'], url_path='availability-slots', permission_classes=[IsAuthenticated])
    def get_availability_slots(self, request, pk=None):
        doctor = self.get_object()
        slots = doctor.availabilities.all() 
        serializer = AvailabilityBlockSerializer(slots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard_overview(self, request):
        doctor = request.user.doctor_profile
        today = timezone.now().date()

        upcoming_appointments = Appointment.objects.filter(
                doctor=doctor,
                date__gte=today,
                status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
            ).order_by('date', 'time')

        past_appointments = Appointment.objects.filter(
            doctor=doctor,
            date__lt=today
        ).order_by('-date', '-time')        

        stats = Appointment.objects.filter(doctor=doctor).aggregate(
            total_appointments=Count('id'),
            pending_count=Count('id', filter=Q(status=Appointment.Status.PENDING)),
            confirmed_count=Count('id', filter=Q(status=Appointment.Status.CONFIRMED)),
            completed_count=Count('id', filter=Q(status=Appointment.Status.COMPLETED)),
            cancelled_count=Count('id', filter=Q(status=Appointment.Status.CANCELLED))
        )

        upcoming_serializer = AppointmentSerializer(upcoming_appointments, many=True)
        past_serializer = AppointmentSerializer(past_appointments, many=True)
    
        return Response({
            "statistics": stats,
            "upcoming_appointments": upcoming_serializer.data,
            "past_appointments": past_serializer.data
        })

class AvailabilityViewSet(viewsets.ModelViewSet):
    serializer_class = AvailabilityBlockSerializer
    permission_classes = [IsAuthenticated, IsDoctorUser]

    def get_queryset(self):
        return AvailabilityBlock.objects.filter(doctor=self.request.user.doctor_profile)

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user.doctor_profile)



