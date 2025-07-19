from typing import Any
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, routers, permissions, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from .models import User
from .services import ActivationService


class UserSerialiser(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(read_only=True)

    class Meta:  # type: ignore
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "password",
            "role",
        ]

    def validate(self, attrs: dict[str, Any]):
        """Change the password for its hash to make Token-based authentication available"""

        attrs["password"] = make_password(attrs["password"])
        attrs["is_active"] = False

        return super().validate(attrs=attrs)


class UserActivationSerializer(serializers.Serializer):
    key = serializers.UUIDField()


class UsersAPIViewSet(viewsets.GenericViewSet):
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        elif self.action == "activate":
            return [permissions.AllowAny()]
        else:
            return [permissions.IsAuthenticated()]

    def list(self, request: Request):
        return Response(UserSerialiser(request.user).data, status=200)

    def create(self, request: Request):
        serializer = UserSerialiser(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Activation process
        activation_service = ActivationService(
            email=getattr(serializer.instance, "email")
        )
        activation_key = activation_service.create_activation_key()
        activation_service.save_activation_information(
            user_id=getattr(serializer.instance, "id"),
            activation_key=activation_key,
        )
        activation_service.send_user_activation_email(activation_key=activation_key)

        return Response(UserSerialiser(serializer.instance).data, status=201)

    @action(methods=["POST"], detail=False)
    def activate(self, request: Request) -> Response:
        serializer = UserActivationSerializer(data=request.data)
        serializer.is_valid()

        activation_service = ActivationService()
        try:
            activation_service.activate_user(
                activation_key=serializer.validated_data["key"]
            )
        except ValueError as error:
            raise ValidationError("Activation link expired") from error

        return Response(data=None, status=204)


router = routers.DefaultRouter()
router.register(r"", UsersAPIViewSet, basename="user")
