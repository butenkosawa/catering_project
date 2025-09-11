from datetime import date

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Dish, OrderStatus, Restaurant


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
