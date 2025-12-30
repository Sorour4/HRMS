from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, UserListSerializer, GroupCreateSerializer
from rest_framework.generics import GenericAPIView, ListAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response
from .permissions import DjangoModelPermissionsWithView
from .models import User
from django.contrib.auth.models import Group
from .permissions import IsAdminGroup
from .groups import setup_hr_groups
from rest_framework import status


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class MeView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        u = request.user
        return Response({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,  
        })


class UserListView(ListAPIView):
    permission_classes = [IsAuthenticated, DjangoModelPermissionsWithView]
    serializer_class = UserListSerializer
    queryset = User.objects.all().order_by("id")


class GroupListCreateView(ListCreateAPIView): #generic?
    permission_classes = [IsAdminGroup]
    serializer_class = GroupCreateSerializer
    queryset = Group.objects.all().order_by("id")


class DefaultHRGroupsView(GenericAPIView):
    permission_classes = [IsAdminGroup]

    def post(self, request, *args, **kwargs):
        counts = setup_hr_groups()
        return Response(
            {"detail": "HR groups seeded.", "counts": counts},
            status=status.HTTP_200_OK
        )