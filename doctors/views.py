from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from .models import DoctorProfile, AvailabilityBlock
from .serializers import DoctorProfileSerializer, AvailabilityBlockSerializer


class DoctorPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 20


@api_view(['GET'])
@permission_classes([AllowAny])
def doctor_list(request):
    queryset = DoctorProfile.objects.select_related('user').filter(user__is_active=True)
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

    paginator = DoctorPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = DoctorProfileSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = DoctorProfileSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def doctor_detail(request, pk):
    try:
        doctor = DoctorProfile.objects.select_related('user').get(pk=pk, user__is_active=True)
    except DoctorProfile.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = DoctorProfileSerializer(doctor)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def doctor_availability(request, pk):
    try:
        doctor = DoctorProfile.objects.get(pk=pk)
    except DoctorProfile.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
    blocks = doctor.availability.all()
    serializer = AvailabilityBlockSerializer(blocks, many=True)
    return Response(serializer.data)
