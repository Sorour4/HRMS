from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, UserListSerializer

from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response
from .permissions import DjangoModelPermissionsWithView
from .models import User


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