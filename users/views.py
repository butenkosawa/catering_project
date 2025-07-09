from rest_framework import viewsets, routers, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication


class UsersAPIViewSet(viewsets.GenericViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response({"message": "OK"}, status=200)


router = routers.DefaultRouter()
router.register(r"", UsersAPIViewSet, basename="user")
