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

from datetime import date
from rest_framework import viewsets, serializers, routers, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django.db import transaction

from .models import Restaurant, Dish, Order, OrderItem, OrderStatus
from users.models import Role, User


class DishSerializer(serializers.ModelSerializer):
    class Meta: # type: ignore
        model = Dish
        exclude = ["restaurant"]


class RestaurantSerializer(serializers.ModelSerializer):
    dishes = DishSerializer(many=True)
    
    class Meta: # type: ignore
        model = Restaurant
        fields = "__all__"


class OrderItemSerializer(serializers.Serializer):
    dish = serializers.PrimaryKeyRelatedField(queryset=Dish.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=20)


class OrderSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(read_only=True)
    items = OrderItemSerializer(many=True)
    eta = serializers.DateField()
    total = serializers.IntegerField(min_value=1, read_only=True)
    status = serializers.ChoiceField(OrderStatus.choices(), read_only=True)

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
        assert type(request.user) == User
        user: User = request.user
        if user.role == Role.ADMIN:
            return True
        else:
            return False


class FoodAPIViewSet(viewsets.GenericViewSet):
    def get_permissions(self):
        
        match self.action:
            case "all_orders":
                return[permissions.IsAuthenticated(), IsAdmin()]
            case _:
                return [permissions.IsAuthenticated()]


    @action(methods=["get"], detail=False)
    def dishes(self, request: Request) -> Response:
        restaurants = Restaurant.objects.all()
        serializer = RestaurantSerializer(restaurants, many=True)
        return Response(data=serializer.data)
    
    # HTTP POST /food/orders/ {}
    #@transaction.atomic    <-- also available
    @action(methods=["post"], detail=False, url_path=r"orders")
    def create_order(self, request: Request) -> Response:
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = Order.objects.create(
                status=OrderStatus.NOT_STARTED,
                user=request.user,
                delivery_provider="uklon",
                eta=serializer.validated_data["eta"],
                total=serializer.calculated_total
            )

            items = serializer.validated_data["items"]

            for dish_order in items:
                # raise ValueError("Some Error Occured")
                instance = OrderItem.objects.create(
                    dish=dish_order["dish"],
                    quantity=dish_order["quantity"],
                    order=order
                )
                print(f"New Dish Order Item is created: {instance.pk}")
        
        print(f"New Food Order is created: {order.pk}. ETA: {order.eta}")

        # TODO: Run Scheduler
        
        return Response(OrderSerializer(order).data, status=201)
        
    # HTTP GET /food/orders/4
    @action(methods=["get"], detail=False, url_path=r"orders/(?P<id>\d+)")
    def retrieve_order(self, request: Request, id: int) -> Response:
        order = Order.objects.get(id=id)
        serializer = OrderSerializer(order)
        return Response(data=serializer.data)
    
    @action(methods=["get"], detail=False, url_path=r"orders")
    def all_orders(self, request: Request) -> Response:
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


router = routers.DefaultRouter()
router.register(prefix="", viewset=FoodAPIViewSet, basename="food")
