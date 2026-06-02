from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer

from .models import DoctorProfile, AvailabilityBlock, DoctorDocument
from .serializers import DoctorProfileSerializer, AvailabilityBlockSerializer


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
            return Response({'error': 'Validation failed', 'field_errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

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


# ===== Public doctor endpoints =====

class DoctorPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 20


@api_view(['GET'])
@permission_classes([AllowAny])
def doctor_list(request):
    queryset = DoctorProfile.objects.select_related('user').filter(user__is_active=True, user__verified=True)
    specialty = request.query_params.get('specialty')
    name = request.query_params.get('name')
    search = request.query_params.get('search')

    if specialty:
        queryset = queryset.filter(specialty__icontains=specialty)
    if name:
        queryset = queryset.filter(
            Q(first_name__icontains=name) | Q(last_name__icontains=name)
        )
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(specialty__icontains=search)
        )

    serializer = DoctorProfileSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PATCH'])
@permission_classes([AllowAny])
def doctor_detail(request, pk):
    if request.method == 'GET':
        try:
            doctor = DoctorProfile.objects.select_related('user').get(pk=pk, user__is_active=True, user__verified=True)
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DoctorProfileSerializer(doctor)
        return Response(serializer.data)

    if request.method == 'PATCH':
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            doctor = DoctorProfile.objects.select_related('user').get(pk=pk, user__is_active=True)
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)

        is_doctor_owner = hasattr(user, 'doctor_profile') and user.doctor_profile.pk == doctor.pk
        if user.role != 'admin' and not is_doctor_owner:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = DoctorProfileSerializer(doctor, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': 'Validation failed', 'field_errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def doctor_availability(request, pk, slot_id=None):
    # GET — public, only verified doctors
    if request.method == 'GET':
        try:
            doctor = DoctorProfile.objects.get(pk=pk, user__is_active=True, user__verified=True)
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)

        blocks = doctor.availability.all()
        if slot_id is not None:
            blocks = blocks.filter(pk=slot_id)
        serializer = AvailabilityBlockSerializer(blocks, many=True)
        return Response(serializer.data)

    # Mutations require auth — allow unverified doctors to manage own slots
    try:
        doctor = DoctorProfile.objects.get(pk=pk, user__is_active=True)
    except DoctorProfile.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not user.is_authenticated:
        return Response({'error': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
    is_doctor_owner = hasattr(user, 'doctor_profile') and user.doctor_profile.pk == doctor.pk
    if user.role != 'admin' and not is_doctor_owner:
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    # POST — create
    if request.method == 'POST':
        serializer = AvailabilityBlockSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': 'Validation failed', 'field_errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(doctor=doctor)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # Operations on a specific slot
    try:
        slot = doctor.availability.get(pk=slot_id)
    except (AvailabilityBlock.DoesNotExist, TypeError):
        return Response({'error': 'Availability slot not found.'}, status=status.HTTP_404_NOT_FOUND)

    # PUT/PATCH — update
    if request.method in ('PUT', 'PATCH'):
        serializer = AvailabilityBlockSerializer(slot, data=request.data, partial=request.method == 'PATCH')
        if not serializer.is_valid():
            return Response({'error': 'Validation failed', 'field_errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    # DELETE
    if request.method == 'DELETE':
        slot.delete()
        return Response({'deleted': True, 'id': slot_id})

    return Response({'error': 'Method not allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


# ====== Doctor Document Upload & Admin Review ======


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_documents(request):
    if not hasattr(request.user, 'doctor_profile'):
        return Response({'error': 'Only doctors can upload documents.'}, status=status.HTTP_403_FORBIDDEN)

    doctor = request.user.doctor_profile

    identity = request.FILES.get('identity_document')
    certificate = request.FILES.get('medical_certificate')

    if not identity or not certificate:
        return Response({'error': 'Both identity_document and medical_certificate are required.'}, status=status.HTTP_400_BAD_REQUEST)

    existing = DoctorDocument.objects.filter(doctor=doctor).first()
    if existing:
        if existing.status != 'rejected':
            return Response({'error': 'Documents already uploaded and pending review.'}, status=status.HTTP_400_BAD_REQUEST)
        existing.identity_document = identity
        existing.medical_certificate = certificate
        existing.status = 'pending'
        existing.rejection_reason = ''
        existing.save()
        doc = existing
    else:
        doc = DoctorDocument.objects.create(
            doctor=doctor,
            identity_document=identity,
            medical_certificate=certificate,
        )

    return Response({
        'id': doc.id,
        'status': doc.status,
        'identity_document': doc.identity_document.url if doc.identity_document else None,
        'medical_certificate': doc.medical_certificate.url if doc.medical_certificate else None,
        'uploaded_at': doc.uploaded_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_list(request):
    user = request.user
    if user.role == 'admin':
        status_filter = request.query_params.get('status')
        docs = DoctorDocument.objects.select_related('doctor__user').all()
        if status_filter:
            docs = docs.filter(status=status_filter)
    elif user.role == 'doctor' and hasattr(user, 'doctor_profile'):
        docs = DoctorDocument.objects.filter(doctor=user.doctor_profile)
    else:
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    data = []
    for d in docs:
        data.append({
            'id': d.id,
            'doctor_id': d.doctor.user_id,
            'doctor_name': f'{d.doctor.first_name} {d.doctor.last_name}',
            'doctor_email': d.doctor.user.email,
            'specialty': d.doctor.specialty,
            'identity_document': d.identity_document.url if d.identity_document else None,
            'medical_certificate': d.medical_certificate.url if d.medical_certificate else None,
            'status': d.status,
            'rejection_reason': d.rejection_reason,
            'uploaded_at': d.uploaded_at.isoformat(),
        })

    return Response(data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def review_document(request, pk):
    if request.user.role != 'admin':
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        doc = DoctorDocument.objects.select_related('doctor').get(pk=pk)
    except DoctorDocument.DoesNotExist:
        return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    if new_status not in ('approved', 'rejected'):
        return Response({'error': 'Status must be "approved" or "rejected".'}, status=status.HTTP_400_BAD_REQUEST)

    doc.status = new_status
    doc.rejection_reason = request.data.get('rejection_reason', '')
    doc.save()

    if new_status == 'approved':
        user = doc.doctor.user
        user.verified = True
        user.save(update_fields=['verified'])

    return Response({
        'id': doc.id,
        'status': doc.status,
        'rejection_reason': doc.rejection_reason,
    })
