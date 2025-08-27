from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView

from food.views import import_dishes, kfc_webhook
from food.views import router as food_router
from food.views import uber_webhook
from users.views import router as users_router

urlpatterns = [
    path("admin/food/dish/import-dishes/", import_dishes, name="import_dishes"),
    path("admin/", admin.site.urls),
    path("auth/token/", TokenObtainPairView.as_view(), name="obtain_token"),
    path("users/", include(users_router.urls)),
    path("food/", include(food_router.urls)),
    path(
        "webhooks/kfc/3d4d05d9-835e-433d-bb3b-e218bcbfa431/",
        kfc_webhook,
    ),
    path(
        "webhooks/uber/e7a684e0-03e3-46ba-97eb-f3604abc494c/",
        uber_webhook,
    ),
]


if settings.DEBUG is True:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [
        # OpenAPI URLS
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        # Optional UI:
        path("api/schema/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
