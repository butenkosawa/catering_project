import enum
from dataclasses import dataclass, asdict

import httpx


class OrderStatus(enum.StrEnum):
    NOT_STARTED = "not_started"
    DELIVERY = "delivery"
    DELIVERED = "delivered"


@dataclass
class OrderRequestBody:
    addresses: list[str]
    comments: list[str]


@dataclass
class OrderResponse:
    id: str
    status: OrderStatus
    location: tuple[float, float]
    addresses: list[str]
    comments: list[str]


class Client:
    # the url of running service
    BASE_URL = "http://uklon-mock:8000/drivers/orders"

    @classmethod
    def create_order(cls, order: OrderRequestBody):
        response: httpx.Response = httpx.post(cls.BASE_URL, json=asdict(order))
        response.raise_for_status()
        return OrderResponse(**response.json())

    @classmethod
    def get_order(cls, order_id: str):
        response: httpx.Response = httpx.get(f"{cls.BASE_URL}/{order_id}")
        response.raise_for_status()
        return OrderResponse(**response.json())
