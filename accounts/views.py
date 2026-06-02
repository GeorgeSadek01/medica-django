from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db.models import Q
from doctors.models import DoctorProfile
from .serializers import RegisterSerializer, UserSerializer, AdminUserUpdateSerializer
from .models import User


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

    refresh = RefreshToken.for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def token(request):
    email = request.data.get('email', '')
    password = request.data.get('password', '')

    user = authenticate(request, username=email, password=password)
    if not user or not user.is_active:
        return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

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
    return Response(UserSerializer(request.user).data)


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
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if request.user.role != 'admin':
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
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
