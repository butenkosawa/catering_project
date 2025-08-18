from dataclasses import dataclass, field, asdict
from time import sleep

from config import celery_app
from shared.cache import CacheService

from .models import Order, Restaurant, OrderItem
from .enums import OrderStatus
from .providers import silpo, kfc
from .mapper import RESTAURANT_EXTERNAL_TO_INTERNAL


@dataclass
class TrackingOrder:
    """
    {
        17.: {
            restaurants: {  // internal Order.id
                1. {  // internal restaurant id
                    status: NOT_STARTED, // internal
                    external_id: 13,
                    request_body: {...},
                },
                2. {  // internal restaurant id
                    status: NOT_STARTED, // internal
                    external_id: 206641bf-a6e5-4cbb-804e-34df757ef0fc,
                    request_body: {...},
                },
            },
            delivery: {...}
        },
        18: ...
    }
    """

    restaurants: dict = field(default_factory=dict)
    delivery: dict = field(default_factory=dict)


def get_tracking_order(order_id: int):
    cache = CacheService()
    payload = cache.get(namespace="orders", key=str(order_id))

    if not isinstance(payload, dict):
        raise ValueError(f"No payload in cache for order {order_id!r}")

    return TrackingOrder(**payload)


def get_internal_status(provider_key: str, status: str) -> OrderStatus:
    """Normalizes external status and maps it to internal.
    Supports variants: 'not started', 'not_started', 'Not-Started', etc.
    """
    if status is None:
        raise ValueError("External status is required")

    mapping = RESTAURANT_EXTERNAL_TO_INTERNAL.get(provider_key, {})

    # normalize: trim, lower, replace spaces/dashes -> underscore
    normalized = str(status).strip().lower().replace(" ", "_").replace("-", "_")

    # Try normalized, then plain lower, then original
    internal = mapping.get(normalized)

    if internal is None:
        # additional log for diagnostics
        print(
            f"Unknown external status for {provider_key}: {status!r}. Known keys: {list(mapping.keys())}"
        )
        raise ValueError(
            f"Unknown external status '{status}' for provider '{provider_key}'"
        )

    return internal


def all_orders_cooked(order_id: int):
    tracking_order = get_tracking_order(order_id)

    print(f"Checking if all orders are cooked: {tracking_order.restaurants}")

    results = all(
        (
            payload["status"] == OrderStatus.COOKED
            for _, payload in tracking_order.restaurants.items()
        )
    )
    return results


@celery_app.task(queue="high_priority")
def order_in_silpo(order_id: int, items):
    """Short polling requests to the Silpo API

    NOTES
    get order from cache
    is external_id?
      no: make order
      yes: get order
    """

    client = silpo.Client()
    cache = CacheService()
    restaurant = Restaurant.objects.get(name="Silpo")

    cooked = False

    while not cooked:
        sleep(1)  # just a delay

        # GET ITEM FROM THE CACHE
        tracking_order = get_tracking_order(order_id)
        # validate
        silpo_order = tracking_order.restaurants.get(str(restaurant.pk))
        if not silpo_order:
            raise ValueError("No Silpo in orders processing")

        # PRINT CURRENT STATUS
        print(f"CURRENT SILPO ORDER STATUS: {silpo_order["status"]}")

        if not silpo_order["external_id"]:
            # MAKE THE FIRST REQUEST IF NOT STARTED
            response: silpo.OrderResponse = client.create_order(
                silpo.OrderRequestBody(
                    order=[
                        silpo.OrderItem(dish=item.dish.name, quantity=item.quantity)
                        for item in items
                    ]
                )
            )
            internal_status: OrderStatus = get_internal_status(
                provider_key="silpo", status=response.status
            )
            # UPDATE CACHE WITH EXTERNAL ID STATUS
            tracking_order.restaurants[str(restaurant.pk)] = {
                "external_id": response.id,
                "status": internal_status,
            }
            cache.set(
                namespace="orders", key=str(order_id), value=asdict(tracking_order)
            )
        else:
            # IF ALREADY HAVE EXTERNAL ID - JUST RETRIEVE THE ORDER
            # PASS EXTERNAL SILPO ORDER ID
            response = client.get_order(silpo_order["external_id"])
            internal_status: OrderStatus = get_internal_status(
                provider_key="silpo", status=response.status
            )
            print(
                f"Tracking for Silpo Order with HTTP GET /api/orders. Status: {internal_status}"
            )

            if silpo_order["status"] != internal_status:
                tracking_order.restaurants[str(restaurant.pk)][
                    "status"
                ] = internal_status
                print(f"Silpo order status changed to {internal_status}")
                cache.set(
                    namespace="orders", key=str(order_id), value=asdict(tracking_order)
                )
                # if started cooking
                if internal_status == OrderStatus.COOKING:
                    Order.objects.filter(id=order_id).update(status=OrderStatus.COOKING)

            if internal_status == OrderStatus.COOKED:
                print("ORDER IS COOKED")
                cooked = True

                # CHECK IF ALL ORDERS ARE COOKED
                if all_orders_cooked(order_id):
                    cache.set(
                        namespace="orders",
                        key=str(order_id),
                        value=asdict(tracking_order),
                        ttl=60,
                    )
                    Order.objects.filter(id=order_id).update(status=OrderStatus.COOKED)


@celery_app.task(queue="high_priority")
def order_in_kfc(order_id: int, items):
    client = kfc.Client()
    cache = CacheService()
    restaurant = Restaurant.objects.get(name="KFC")

    # GET TRACKING ORDER FROM THE CACHE
    tracking_order = get_tracking_order(order_id)

    # UPDATE CACHE WITH EXTERNAL ID AND STATE
    tracking_order.restaurants[str(restaurant.pk)] = {
        "external_ID": "MOCK",
        "status": OrderStatus.COOKED,
    }

    print("Created MOCKED KFC Order. External ID: 'MOCK', Status: 'COOKED'")
    cache.set(namespace="orders", key=str(order_id), value=asdict(tracking_order))

    # TODO: Implement WEBHooks for KFC

    # CHECK IF ALL ORDERS ARE COOKED
    if all_orders_cooked(order_id):
        cache.set(
            namespace="orders", key=str(order_id), value=asdict(tracking_order), ttl=60
        )
        Order.objects.filter(id=order_id).update(status=OrderStatus.COOKED)


def schedule_order(order: Order):
    # define services and data state
    cache = CacheService()
    tracking_order = TrackingOrder()

    items_by_restaurants = order.items_by_restaurant()
    for restaurant, items in items_by_restaurants.items():
        # update tracking order instance to be saved to the cache
        tracking_order.restaurants[str(restaurant.pk)] = {
            "external_id": None,
            "status": OrderStatus.NOT_STARTED,
        }

    # update cache instance only once in the end
    cache.set(namespace="orders", key=str(order.pk), value=asdict(tracking_order))

    # start processing after cache is complete
    for restaurant, items in items_by_restaurants.items():
        match restaurant.name.lower():
            case "silpo":
                order_in_silpo.delay(order.pk, items)  # type: ignore[attr-defined]
                # or
                # order_in_silpo.apply_async()
            case "kfc":
                order_in_kfc.delay(order.pk, items)  # type: ignore[attr-defined]
            case _:
                raise ValueError(
                    f"Restaurant {restaurant.name} is not available for processing"
                )
