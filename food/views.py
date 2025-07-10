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

from django.shortcuts import render
from rest_framework import viewsets, serializers, routers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Restaurant, Dish, Order, OrderItem, OrderStatus


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
    items = OrderItemSerializer(many=True)
    eta = serializers.DateField()
    total = serializers.IntegerField(min_value=1, read_only=True)
    status = serializers.ChoiceField(OrderStatus.choices(), read_only=True)


class FoodAPIViewSet(viewsets.GenericViewSet):
    @action(methods=["get"], detail=False)
    def dishes(self, request: Request) -> Response:
        restaurants = Restaurant.objects.all()
        serializer = RestaurantSerializer(restaurants, many=True)
        return Response(data=serializer.data)
    
    # HTTP POST /food/orders/ {}
    @action(methods=["post"], detail=False, url_path=r"orders")
    def create_orders(self, request: Request) -> Response:
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = Order.objects.create(
            status=OrderStatus.NOT_STARTED,
            user=request.user,
            delivery_provider="uklon",
            eta=serializer.validated_data["eta"]
        )

        items = serializer.validated_data["items"]

        for dish_order in items:
            instance = OrderItem.objects.create(
                dish=dish_order["dish"],
                quantity=dish_order["quantity"],
                order=order
            )
            print(f"New Dish Order Item is created: {instance.pk}")
        
        print(f"New Food Order is created: {order.pk}. ETA: {order.eta}")

        # TODO: Run Scheduler
        
        return Response(
            data={
                "id": order.pk, 
                "status": order.status,
                "eta": order.eta,
                "total": order.total
            }, 
            status=201
        )
        
    # HTTP GET /food/orders/4
    @action(methods=["get"], detail=False, url_path=r"orders/(?P<id>\d+)")
    def retrieve_order(self, request: Request, id: int) -> Response:
        order = Order.objects.get(id=id)
        serializer = OrderSerializer(order)
        return Response(data=serializer.data)


router = routers.DefaultRouter()
router.register(prefix="", viewset=FoodAPIViewSet, basename="food")
