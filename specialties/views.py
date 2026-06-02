from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import Specialty
from .serializers import SpecialtySerializer


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def specialty_list(request):

    if request.method == 'GET':
        specialties = Specialty.objects.all()
        serializer = SpecialtySerializer(specialties, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        if not request.user.is_authenticated or request.user.role != 'admin':
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = SpecialtySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def specialty_detail(request, pk):

    if request.user.role != 'admin':
        return Response(
            {'error': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        specialty = Specialty.objects.get(pk=pk)
    except Specialty.DoesNotExist:
        return Response(
            {'error': 'Specialty not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        return Response(SpecialtySerializer(specialty).data)

    if request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = SpecialtySerializer(
            specialty,
            data=request.data,
            partial=partial
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        specialty_id = specialty.id
        specialty.delete()
        return Response({'deleted': True, 'id': specialty_id})