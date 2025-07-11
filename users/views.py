from typing import Any
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, routers, permissions, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User


class UserSerialiser(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(read_only=True)

    class Meta: # type: ignore
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "password",
            "role"
        ]
    
    def validate(self, attrs: dict[str, Any]):
        """Change the password for its hash to make Token-based authentication avaliable"""

        attrs["password"] = make_password(attrs["password"])

        return super().validate(attrs=attrs)


class UsersAPIViewSet(viewsets.GenericViewSet):
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        else:
            return [permissions.IsAuthenticated()]

    def list(self, request: Request):
        return Response(UserSerialiser(request.user).data, status=200)

    def create(self, request: Request):
        serializer = UserSerialiser(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerialiser(serializer.instance).data, status=201)


router = routers.DefaultRouter()
router.register(r"", UsersAPIViewSet, basename="user")
