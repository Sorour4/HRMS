from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsAdmin
from .models import User
from .serializers import UserListSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    return Response({
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "role": u.role,
    })

@api_view(["GET"])
@permission_classes([IsAdmin])
def list_users(request):
    qs = User.objects.all().order_by("id")
    data = UserListSerializer(qs, many=True).data
    return Response(data)