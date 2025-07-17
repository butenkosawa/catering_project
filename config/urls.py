from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from users.views import router as users_router
from food.views import router as food_router
from food.views import import_dishes


urlpatterns = [
    path("admin/food/dish/import-dishes/", import_dishes, name="import_dishes"),
    path("admin/", admin.site.urls),
    path("auth/token/", TokenObtainPairView.as_view(), name="obtain_token"),
    path("users/", include(users_router.urls)),
    path("food/", include(food_router.urls)),
]
