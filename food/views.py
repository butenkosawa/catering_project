"""
=============================
CREATE ORDER FLOW
=============================
>>> HTTP Request
{
    "items": [
        {
        "dish": 3,
        "quantity": 2
        },
        {
        "dish": 4,
        "quantity": 1
        }
    ],
    "eta": "2025-07-10"
}

<<< HTTP Response
{
    "items": [
        {
        "dish": 3,
        "quantity": 2
        },
        {
        "dish": 4,
        "quantity": 1
        }
    ],
    "eta": "2025-07-10",
    "id": 1,
    "status": "not_started"
}
"""

import csv
import io
import json
from dataclasses import asdict
from datetime import date
from typing import Any

from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, routers, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response

from config.settings import CACHE_TTL
from shared.cache import CacheService
from users.models import Role, User

from .enums import DeliveryProvider
from .models import Dish, Order, OrderItem, OrderStatus, Restaurant
from .services import all_orders_cooked, get_tracking_order, schedule_order


class DishCreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = "__all__"

    def validate_price(self, value: int):
        if value < 1:
            raise ValidationError("PRICE must be greater than 1 (in cents)")
        return value


class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        exclude = ["restaurant"]


class RestaurantSerializer(serializers.ModelSerializer):
    dishes = DishSerializer(many=True)

    class Meta:
        model = Restaurant
        fields = "__all__"


class OrderItemSerializer(serializers.Serializer):
    dish = serializers.PrimaryKeyRelatedField(queryset=Dish.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=20)


class OrderSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    items = OrderItemSerializer(many=True)
    eta = serializers.DateField()
    total = serializers.IntegerField(min_value=1, read_only=True)
    status = serializers.ChoiceField(OrderStatus.choices(), read_only=True)
    delivery_provider = serializers.CharField()

    @property
    def calculated_total(self) -> int:
        total = 0

        for item in self.validated_data["items"]:
            dish: Dish = item["dish"]
            quantity: int = item["quantity"]
            total += dish.price * quantity

        return total

    # validate_<any-fieldname>
    # def validate_items(self, value: Any):
    #     raise ValidationError("Some error")

    def validate_eta(self, value: date):
        if (value - date.today()).days < 1:
            raise ValidationError("ETA must be min 1 day after today")
        return value


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        assert type(request.user) is User
        user: User = request.user
        if user.role == Role.ADMIN:
            return True
        else:
            return False


class BaseFilters:
    @staticmethod
    def snake_to_camel_case(value: str) -> str:
        parts = value.split("_")
        return parts[0] + "".join(word.capitalize() for word in parts[1:])

    @staticmethod
    def camel_to_snake_case(value: str) -> str:
        result = []
        for i, char in enumerate(value):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result)

    def __init__(self, **kwargs) -> None:
        errors: dict[str, dict[str, Any]] = {"queryParams": {}}

        for key, value in kwargs.items():
            _key: str = self.camel_to_snake_case(key)
            if _key in ("limit", "offset", "page", "size"):
                continue

            try:
                extractor = getattr(self, f"extract_{_key}")
            except AttributeError:
                errors["queryParams"][
                    key
                ] = f"You forgot to define `extract_{_key}` method in your class `{self.__class__.__name__}`"
                raise ValidationError(errors)

            try:
                _extracted_value = extractor(value)
            except ValidationError as error:
                errors["queryParams"][key] = str(error)
            else:
                setattr(self, _key, _extracted_value)

        if errors["queryParams"]:
            raise ValidationError(errors)


class FoodFilters(BaseFilters):
    # def __init__(self, status: str | None = None, **kwargs):
    #     super().__init__(status=status, **kwargs)

    def extract_delivery_provider(
        self, provider: str | None = None
    ) -> DeliveryProvider | None:
        if provider is None:
            return None
        provider_name = provider.upper()
        try:
            return DeliveryProvider[provider_name]
        except KeyError:
            raise ValidationError(f"Provider {provider} is not supported")

    def extract_status(self, status: str | None = None) -> OrderStatus | None:
        if status is None:
            return None
        status_value = status.upper()
        try:
            return OrderStatus[status_value]
        except KeyError:
            raise ValidationError(f"Status {status} is not supported")

    def extract_user_id(self, user_id: str | None = None) -> int | None:
        if user_id is None:
            return None
        try:
            return int(user_id)
        except ValueError:
            raise ValidationError("User ID must be a number")

    def extract_min_total(self, min_total: str | None = None) -> int | None:
        if min_total is None:
            return None
        try:
            return int(min_total)
        except ValueError:
            raise ValidationError("Min total must be a number")

    def extract_max_total(self, max_total: str | None = None) -> int | None:
        if max_total is None:
            return None
        try:
            return int(max_total)
        except ValueError:
            raise ValidationError("Max total must be a number")

    def extract_eta_from(self, eta_from: str | None = None) -> date | None:
        if eta_from is None:
            return None
        try:
            return date.fromisoformat(eta_from)
        except ValueError:
            raise ValidationError("Date must be in `YYYY-MM-DD` format")

    def extract_eta_to(self, eta_to: str | None = None) -> date | None:
        if eta_to is None:
            return None
        try:
            return date.fromisoformat(eta_to)
        except ValueError:
            raise ValidationError("Date must be in `YYYY-MM-DD` format")


class FoodAPIViewSet(viewsets.GenericViewSet):
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action == "orders" and self.request.method == "GET":
            return [permissions.IsAuthenticated(), IsAdmin()]
        elif self.action == "dishes" and self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsAdmin()]
        else:
            return [permissions.IsAuthenticated()]

    @action(methods=["get", "post"], detail=False)
    def dishes(self, request: Request) -> Response:
        if request.method == "GET":
            # Apply caching only for GET requests
            response = self._get_dishes_with_cache(request)
            return response

        elif request.method == "POST":
            serializer = DishCreatorSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            dish = Dish.objects.create(
                name=serializer.validated_data["name"],
                price=serializer.validated_data["price"],
                restaurant=serializer.validated_data["restaurant"],
            )
            print(f"New Dish is created: {dish.pk}: {dish.name} | {dish.price}")
            return Response(DishSerializer(dish).data, status=201)

        return Response({"detail": f"Method {request.method} not allowed."}, status=405)

    @method_decorator(cache_page(30))
    def _get_dishes_with_cache(self, request: Request) -> Response:
        dish_name = request.query_params.get("name")

        if not dish_name:
            restaurants = Restaurant.objects.all()
        else:
            restaurants = Restaurant.objects.prefetch_related(
                Prefetch(
                    "dishes",
                    queryset=Dish.objects.filter(name__icontains=dish_name),
                )
            ).all()

        page = self.paginate_queryset(restaurants)
        if page is not None:
            serializer = RestaurantSerializer(page, many=True)
            return self.get_paginated_response(data=serializer.data)

        serializer = RestaurantSerializer(restaurants, many=True)
        # import time
        # time.sleep(3)
        return Response(data=serializer.data)

    def all_orders(self, request: Request) -> Response:
        filters = FoodFilters(**request.query_params.dict())
        orders = Order.objects.select_related("user").all()

        filter_mapping = {
            "delivery_provider": "delivery_provider",
            "status": "status",
            "user_id": "user_id",
            "min_total": "total__gte",
            "max_total": "total__lte",
            "eta_from": "eta__gte",
            "eta_to": "eta__lte",
        }

        filter_kwargs = {}
        for filter_attr, django_filter in filter_mapping.items():
            if hasattr(filters, filter_attr):
                value = getattr(filters, filter_attr)
                if value is not None:
                    filter_kwargs[django_filter] = value

        if filter_kwargs:
            orders = orders.filter(**filter_kwargs)

        # =====================
        # PageNumberPagination
        # =====================
        # paginator = PageNumberPagination()
        # paginator.page_size = 2
        # paginator.page_size_query_param = "size"
        # page = paginator.paginate_queryset(orders, request, view=self)

        # =====================
        # LimitOffsetPagination
        # =====================
        page = self.paginate_queryset(orders)

        if page is not None:
            serializer = OrderSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def create_order(self, request: Request) -> Response:
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not isinstance(request.user, User):
            raise ValidationError("Only authenticated users can create orders.")

        with transaction.atomic():
            order = Order.objects.create(
                status=OrderStatus.NOT_STARTED,
                user=request.user,
                delivery_provider=serializer.validated_data["delivery_provider"],
                eta=serializer.validated_data["eta"],
                total=serializer.calculated_total,
            )
            items = serializer.validated_data["items"]

            for dish_order in items:
                # raise ValueError("Some Error Occurred")
                instance = OrderItem.objects.create(
                    dish=dish_order["dish"],
                    quantity=dish_order["quantity"],
                    order=order,
                )
                print(f"New Dish Order Item is created: {instance.pk}")

        print(f"New Food Order is created: {order.pk}. ETA: {order.eta}")

        schedule_order(order)

        return Response(OrderSerializer(order).data, status=201)

    # HTTP POST /food/orders/
    # @transaction.atomic    <-- also available
    @action(methods=["get", "post"], detail=False)
    def orders(self, request: Request) -> Response:
        if request.method == "POST":
            return self.create_order(request)
        else:
            return self.all_orders(request)

    # HTTP GET /food/orders/4
    @action(methods=["get"], detail=False, url_path=r"orders/(?P<id>\d+)")
    def retrieve_order(self, request: Request, id: int) -> Response:
        order = Order.objects.get(id=id)
        serializer = OrderSerializer(order)
        return Response(data=serializer.data)


def import_dishes(request):
    if request.method != "POST":
        raise ValueError(f"Method `{request.method}` is not allowed on this resource")
    elif request.user.role != Role.ADMIN:
        raise ValueError(
            f"User role `{request.user.role}` is not allowed on this resource"
        )

    csv_file = request.FILES.get("file")
    if csv_file is None:
        raise ValueError("No CSV File Provided")

    decoded = csv_file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    total = 0

    for row in reader:
        restaurant_name = row["restaurant"]
        try:
            rest = Restaurant.objects.get(name__icontains=restaurant_name.lower())
        except Restaurant.DoesNotExist:
            print(f"Skipping restaurant {restaurant_name}")
            continue

        print(f"Restaurant {rest} found")
        Dish.objects.create(name=row["name"], price=int(row["price"]), restaurant=rest)
        total += 1

    print(f"{total} dishes uploaded to the database")
    return redirect(request.META.get("HTTP_REFERER", "/"))


@csrf_exempt
def kfc_webhook(request):
    """Process KFC Order webhooks."""

    print("KFC Webhook is Handled")

    data: dict = json.loads(json.dumps(request.POST))

    cache = CacheService()
    restaurant = Restaurant.objects.get(name="KFC")
    kfc_cache_order = cache.get("kfc_orders", key=data["id"])

    # get internal order from the mapping
    # add logging if order wasn't found

    order: Order = Order.objects.get(id=kfc_cache_order["internal_order_id"])
    tracking_order = get_tracking_order(order.pk)
    tracking_order.restaurants[str(restaurant.pk)] |= {
        "external_id": data["id"],
        "status": OrderStatus.COOKED,
    }

    cache.set(
        namespace="orders",
        key=str(order.pk),
        value=asdict(tracking_order),
        ttl=CACHE_TTL["ORDER_DATA"],
    )

    all_orders_cooked(order.pk)

    return JsonResponse({"message": "ok"})


@csrf_exempt
def uber_webhook(request):
    """Process UBER Order webhooks."""

    print("UBER Webhook is Handled")

    data: dict = json.loads(json.dumps(request.POST))

    cache = CacheService()
    uber_cache_order = cache.get("uber_orders", key=data["id"])

    # get internal order from the mapping
    # add logging if order wasn't found

    order: Order = Order.objects.get(id=uber_cache_order["internal_order_id"])
    tracking_order = get_tracking_order(order.pk)

    if data["location"] == "delivery":
        tracking_order.delivery |= {
            "location": data["location"],
            "status": OrderStatus.DELIVERY,
        }
    else:
        tracking_order.delivery |= {
            "location": data["location"],
            "status": OrderStatus.DELIVERED,
        }
        print(f"🏁 UBER [{order.status}]: 📍 {data["location"]}")

    cache.set(
        namespace="orders",
        key=str(order.pk),
        value=asdict(tracking_order),
        ttl=CACHE_TTL["ORDER_DATA"],
    )
    order.status = OrderStatus.DELIVERED
    order.save()

    return JsonResponse({"message": "ok"})


router = routers.DefaultRouter()
router.register(prefix="", viewset=FoodAPIViewSet, basename="food")
