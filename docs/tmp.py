from uuid import UUID
import enum
from typing import Literal


DeliveryProvider = Literal["Uklon", "Uber"]


class OrderStatus(enum.StrEnum):
    WAITING = enum.auto()
    COOKING = enum.auto()
    DELIVERY = enum.auto()
    DELIVERED = enum.auto()
    FAILED = enum.auto()
    CANCELLED_BY_CUSTOMER = enum.auto()
    CANCELLED_BY_MANAGER = enum.auto()
    CANCELLED_BY_ADMIN = enum.auto()
    CANCELLED_BY_RESTAURANT = enum.auto()
    CANCELLED_BY_DRIVER = enum.auto()


class Dish:
    name: str
    description: str
    kkal: int
    price: int


class DishOrder:
    dishes: list[Dish]
    total: int


class DeliveryOrder:
    provider: DeliveryProvider
    total: int


class User:
    id: int
    email: str
    password: str
    address: str


class Order:
    id: UUID
    status: OrderStatus
    total: int
    dishes: DishOrder
    delivery: DeliveryOrder
    customer: User
