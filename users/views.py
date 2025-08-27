from typing import Any

from django.contrib.auth.hashers import make_password
from rest_framework import permissions, routers, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle  # BaseThrottle
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User
from .services import ActivationService, send_email


class UserSerialiser(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(read_only=True)

    class Meta:
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
    email = serializers.EmailField()


class UserResourseThrotling(UserRateThrottle):
    rate = "100/minute"


# class AdvancedThrotling(BaseThrottle):
#     def __init__(self):
#         self.history = {}

#     def allow_request(self, request: Request, view: permissions.APIView) -> bool:
#         from time import time

#         ident = self.get_ident(request)  # Client IP
#         now = time()
#         window = 60  # 1minute
#         limit = 10  # max 10 request

#         history = self.history.get(ident, [])
#         history = [ts for ts in history if ts > now - window]

#         if len(history) >= limit:
#             return False

#         history.append(now)
#         self.history[ident] = history

#         return True


class UsersAPIViewSet(viewsets.GenericViewSet):
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.action in ("create", "activate"):
            return [permissions.AllowAny()]
        else:
            return [permissions.IsAuthenticated()]

    # def get_throtles(self):
    #     if self.action in ("create", "activate"):
    #         return [UserResourseThrotling()]
    #     else:
    #         return [...]

    def list(self, request: Request):
        return Response(UserSerialiser(request.user).data, status=200)

    def create(self, request: Request):
        serializer = UserSerialiser(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        email = getattr(serializer.instance, "email")

        # Activation process
        activation_service = ActivationService(email=email)
        activation_key = activation_service.create_activation_key()
        activation_service.save_activation_information(
            user_id=getattr(serializer.instance, "id"),
            activation_key=str(activation_key),
        )
        send_email.delay(email=email, activation_key=str(activation_key))

        return Response(UserSerialiser(serializer.instance).data, status=201)

    @action(methods=["POST"], detail=False)
    def activate(self, request: Request) -> Response:
        serializer = UserActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        key = serializer.validated_data["key"]

        try:
            user = User.objects.get(email=email, is_active=False)
        except User.DoesNotExist:
            return Response(
                {"detail": f"User `{email}` does not exists or is already active"},
                status=404,
            )

        activation_service = ActivationService(email=email)

        try:
            activation_service.activate_user(activation_key=key)
        except ValueError:
            activation_service.resend_activation_link(user)
            return Response(
                {"detail": f"Key `{key}` does not exist. A new activation key has been sent to `{email}`"},
                status=404,
            )
        else:
            activation_service.remove_activation_key(activation_key=key)

        return Response(data=None, status=204)


router = routers.DefaultRouter()
router.register(r"", UsersAPIViewSet, basename="user")
