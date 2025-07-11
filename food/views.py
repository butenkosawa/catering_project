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


class DishCreaterSerializer(serializers.ModelSerializer):
    class Meta: # type: ignore
        model = Dish
        fields = "__all__"
    
    def validate_price(self, value: int):
        if value < 1:
            raise ValidationError("PRICE must be greater than 1 (in cents)")
        return value


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
        if self.action == "orders" and self.request.method == "GET":
            return[permissions.IsAuthenticated(), IsAdmin()]
        elif self.action == "dishes" and self.request.method == "POST":
            return[permissions.IsAuthenticated(), IsAdmin()]
        else:
            return [permissions.IsAuthenticated()]

    @action(methods=["get", "post"], detail=False)
    def dishes(self, request: Request) -> Response:
        if request.method == "GET":
            restaurants = Restaurant.objects.all()
            serializer = RestaurantSerializer(restaurants, many=True)
            return Response(data=serializer.data)
        
        elif request.method == "POST":
            serializer = DishCreaterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            dish = Dish.objects.create(
                name=serializer.validated_data["name"],
                price=serializer.validated_data["price"],
                restaurant=serializer.validated_data["restaurant"]
            )
            print(f"New Dish is created: {dish.pk}: {dish.name} | {dish.price}")
            return Response(DishSerializer(dish).data, status=201)
        
        return Response({"detail": f"Method {request.method} not allowed."}, status=405)
    
    # HTTP POST /food/orders/ {}
    #@transaction.atomic    <-- also available
    @action(methods=["get", "post"], detail=False)
    def orders(self, request: Request) -> Response:
        if request.method == "GET":
            orders = Order.objects.all()
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)
        
        elif request.method ==  "POST":
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
        
        return Response({"detail": f"Method {request.method} not allowed."}, status=405) 
        
    # HTTP GET /food/orders/4
    @action(methods=["get"], detail=False, url_path=r"orders/(?P<id>\d+)")
    def retrieve_order(self, request: Request, id: int) -> Response:
        order = Order.objects.get(id=id)
        serializer = OrderSerializer(order)
        return Response(data=serializer.data)


router = routers.DefaultRouter()
router.register(prefix="", viewset=FoodAPIViewSet, basename="food")
