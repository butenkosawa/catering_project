from rest_framework import viewsets, routers, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model


class UsersAPIViewSet(viewsets.GenericViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response({"message": "OK"}, status=200)
    
    def create(self, request):
        User = get_user_model()

        email = request.data.get("email")
        password = request.data.get("password")
        phone_number = request.data.get("phone_number")
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")

        if not email or not password:
            return Response(
                {
                    "error": "Email, password, phone, first and last names required"
                }, 
                status=400
            )
        user = User.objects.create_user(
            email=email, 
            password=password,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name
            )
        
        return Response(
            {
                "id": user.id,
                "email": user.email,
                "phone_number": user.phone_number,
                "first_name": user.first_name,
                "last_name": user.last_name              
            }, 
            status=201
        )


router = routers.DefaultRouter()
router.register(r"", UsersAPIViewSet, basename="user")
