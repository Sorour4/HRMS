from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import( 
    CustomTokenObtainPairSerializer,
    UserListSerializer,
    GroupCreateSerializer,
    PermissionListSerializer,
    GroupPermissionIdsSerializer,
    UserGroupIdsSerializer,)
from rest_framework.generics import GenericAPIView, ListAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response
from .permissions import DjangoModelPermissionsWithView
from .models import User
from django.contrib.auth.models import Group
from .permissions import IsAdminGroup
from .groups import setup_hr_groups
from rest_framework import status
from django.contrib.auth.models import Permission


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
    

class PermissionListView(ListAPIView):
    permission_classes = [IsAdminGroup]
    serializer_class = PermissionListSerializer
    queryset = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label", "content_type__model", "codename"
    )


class GroupAddPermissionsView(GenericAPIView):
    permission_classes = [IsAdminGroup]
    serializer_class = GroupPermissionIdsSerializer

    def post(self, request, pk):
        group = Group.objects.get(pk=pk)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        perms = Permission.objects.filter(id__in=ser.validated_data["permission_ids"])
        group.permissions.add(*perms)

        return Response(
            {"detail": "Permissions added.", "group_id": group.id, "permission_ids": ser.validated_data["permission_ids"]},
            status=status.HTTP_200_OK,
        )
    

class GroupRemovePermissionsView(GenericAPIView):
    permission_classes = [IsAdminGroup]
    serializer_class = GroupPermissionIdsSerializer

    def post(self, request, pk):
        group = Group.objects.get(pk=pk)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        perms = Permission.objects.filter(id__in=ser.validated_data["permission_ids"])
        group.permissions.remove(*perms)

        return Response(
            {
                "detail": "Permissions removed.",
                "group_id": group.id,
                "permission_ids": ser.validated_data["permission_ids"],
            },
            status=status.HTTP_200_OK,
        )
    

class UserAddGroupsView(GenericAPIView):
    permission_classes = [IsAdminGroup]
    serializer_class = UserGroupIdsSerializer

    def post(self, request, pk):
        user = User.objects.get(pk=pk)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        groups = Group.objects.filter(id__in=ser.validated_data["group_ids"])
        user.groups.add(*groups)

        return Response(
            {"detail": "Groups added.", "user_id": user.id, "group_ids": ser.validated_data["group_ids"]},
            status=status.HTTP_200_OK,
        )


class UserRemoveGroupsView(GenericAPIView):
    permission_classes = [IsAdminGroup]
    serializer_class = UserGroupIdsSerializer

    def post(self, request, pk):
        user = User.objects.get(pk=pk)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        groups = Group.objects.filter(id__in=ser.validated_data["group_ids"])
        user.groups.remove(*groups)

        return Response(
            {"detail": "Groups removed.", "user_id": user.id, "group_ids": ser.validated_data["group_ids"]},
            status=status.HTTP_200_OK,
        )


class UserDetailWithAuthView(GenericAPIView):
    permission_classes = [IsAdminGroup]

    def get(self, request, pk):
        u = User.objects.get(pk=pk)

        return Response({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "groups": list(u.groups.values_list("name", flat=True)),
            "permissions": sorted(u.get_all_permissions()),
        })