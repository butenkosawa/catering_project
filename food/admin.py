from django.contrib import admin

from .models import Dish, Order, OrderItem, Restaurant

admin.site.register(Restaurant)
admin.site.register(OrderItem)


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "restaurant", "id")
    search_fields = ("name",)
    list_filter = ("name", "restaurant")
    # actions = ("import_csv",)


class DishOrderItemInline(admin.TabularInline):
    model = OrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "id", "status")
    inlines = (DishOrderItemInline,)
