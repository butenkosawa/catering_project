from django.conf import settings
from django.db import models

from .enums import OrderStatus


class Restaurant(models.Model):
    class Meta:
        db_table = "restaurants"

    name = models.CharField(max_length=255, null=False)
    address = models.TextField(null=False)

    def __str__(self) -> str:
        return self.name


class Dish(models.Model):
    class Meta:
        db_table = "dishes"

    name = models.CharField(max_length=255, null=False)
    price = models.IntegerField(null=False)
    restaurant = models.ForeignKey("Restaurant", on_delete=models.CASCADE, related_name="dishes")

    def __str__(self) -> str:
        return self.name


class Order(models.Model):
    class Meta:
        db_table = "orders"

    status = models.CharField(max_length=50, choices=OrderStatus.choices(), default=OrderStatus.NOT_STARTED)
    delivery_provider = models.CharField(max_length=20, null=True, blank=True)
    eta = models.DateField()
    total = models.PositiveIntegerField(null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")

    def __str__(self) -> str:
        return f"[{self.pk}] {self.status} for {self.user.email}"

    def items_by_restaurant(self) -> dict["Restaurant", models.QuerySet["OrderItem"]]:
        results = {}

        # get all items for this order, optimize the query
        qs = self.items.select_related("dish__restaurant")

        # N+1
        restaurants = {item.dish.restaurant for item in qs}

        for restaurant in restaurants:
            results[restaurant] = qs.filter(dish__restaurant=restaurant)

        return results

    def delivery_meta(self) -> list[tuple[str, str]]:
        """Return addresses without duplicates."""

        return list(
            self.items.select_related("dish__restaurant")
            .values_list(
                "dish__restaurant__name",
                "dish__restaurant__address",
            )
            .distinct()
        )


class OrderItem(models.Model):
    class Meta:
        db_table = "order_items"

    quantity = models.SmallIntegerField()
    dish = models.ForeignKey("Dish", on_delete=models.CASCADE)
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="items")

    def __str__(self) -> str:
        return f"[{self.order.pk}] {self.dish.name}: {self.quantity}"
