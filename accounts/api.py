from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsAdmin
from .models import User
from .serializers import UserListSerializer

# TODO: in Django it's always better to follow the framework naming and convenstion 
# as long as we are going with the framework way of doing things, there is no 
# meaning of having a file api.py and views.py there is no dofference.
# move these views to view.py and re-implement then using class based 
# views (GenericAPIView, APIView)
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