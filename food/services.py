from dataclasses import dataclass, field, asdict
from time import sleep
from threading import Thread

from config import celery_app
from shared.cache import CacheService

from .models import Order, Restaurant, OrderItem
from .enums import OrderStatus
from .providers import silpo, kfc, uklon
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
            delivery: {
                location: (..., ...),
                status: NOT_STARTED, DELIVERY, DELIVERED
            }
        },
        18: ...
    }
    """

    restaurants: dict = field(default_factory=dict)
    delivery: dict = field(default_factory=dict)


def all_orders_cooked(order_id: int):
    cache = CacheService()
    tracking_order = TrackingOrder(**cache.get(namespace="orders", key=str(order_id)))
    print(f"Checking if all orders are cooked: {tracking_order.restaurants}")

    if all(
        (
            payload["status"] == OrderStatus.COOKED
            for _, payload in tracking_order.restaurants.items()
        )
    ):
        Order.objects.filter(id=order_id).update(status=OrderStatus.COOKED)
        print("✅ All orders are cooked")
        order_delivery.delay(order_id)
    else:
        print("Not all the orders are cooked")


@celery_app.task(queue="default")
def order_delivery(order_id: int):
    """Using random provider (or now only Uklon) - stard processing delivery order"""

    print("🚚 DELIVERY PROCESSING STARTED")

    provider = uklon.Client()
    cache = CacheService()
    order = Order.objects.get(id=order_id)

    # update Order state
    order.status = OrderStatus.DELIVERY_LOOKUP
    order.save()

    # prepae data for the first request
    addresses = []
    comments = []

    for rest_name, address in order.delivery_meta():
        addresses.append(address)
        comments.append(f"Delivery to the {rest_name}")

    # NOTE: Only UKLON is currently supported so no selection in here.

    order.status = OrderStatus.DELIVERY
    order.save()

    _response: uklon.OrderResponse = provider.create_order(
        uklon.OrderRequestBody(addresses=addresses, comments=comments)
    )

    tracking_order = TrackingOrder(**cache.get(namespace="orders", key=str(order.pk)))
    tracking_order.delivery["status"] = OrderStatus.DELIVERY
    tracking_order.delivery["location"] = _response.location

    current_status: uklon.OrderStatus = _response.status

    while current_status != uklon.OrderStatus.DELIVERED:
        response = provider.get_order(_response.id)

        print(f"🚙 UKLON [{response.status}]: 📍 {response.location}")

        if current_status == response.status:
            sleep(1)
            continue

        current_status = response.status  # DELIVERY, DELIVERED

        tracking_order.delivery["location"] = response.location

        # update cache
        cache.set(namespace="orders", key=str(order.pk), value=asdict(tracking_order))

    print(f"🏁 UKLON [{response.status}]: 📍 {response.location}")

    # update storage
    Order.objects.filter(id=order_id).update(status=OrderStatus.DELIVERED)

    # update the cache
    tracking_order.delivery["status"] = OrderStatus.DELIVERED
    cache.set(namespace="orders", key=str(order_id), value=asdict(tracking_order))

    print("✅ DONE with Delivery")


@celery_app.task(queue="default")
def order_in_silpo(order_id: int, items):
    """Short polling requests to the Silpo API

    NOTES
    get order from cache
    is extenal_id?
      no: make order
      yes: get order
    """

    client = silpo.Client()
    cache = CacheService()
    restaurant = Restaurant.objects.get(name="Silpo")

    def get_internal_status(status: str) -> OrderStatus:
        """Normalizes external status and maps it to internal.
        Supports variants: 'not started', 'not_started', 'Not-Started', etc.
        """
        if status is None:
            raise ValueError("External status is required")

        provider_key = "silpo"
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

    cooked = False

    while not cooked:
        sleep(1)  # just a delay

        # GET ITEM FROM THE CACHE
        tracking_order = TrackingOrder(
            **cache.get(namespace="orders", key=str(order_id))
        )
        # validate
        silpo_order = tracking_order.restaurants.get(str(restaurant.pk))
        if not silpo_order:
            raise ValueError("No Silpo in orders processing")

        # PRINT CURRENT STATUS
        print(f"CURRENT SILPO ORDER STATUS: {silpo_order["status"]}")

        if not silpo_order["external_id"]:
            # ✨ MAKE THE FIRST REQUEST IF NOT STARTED
            response: silpo.OrderResponse = client.create_order(
                silpo.OrderRequestBody(
                    order=[
                        silpo.OrderItem(dish=item.dish.name, quantity=item.quantity)
                        for item in items
                    ]
                )
            )
            internal_status: OrderStatus = get_internal_status(response.status)

            # UPDATE CACHE WITH EXTERNAL ID STATUS
            tracking_order.restaurants[str(restaurant.pk)] = {
                "external_id": response.id,
                "status": internal_status,
            }
            cache.set(
                namespace="orders", key=str(order_id), value=asdict(tracking_order)
            )
        else:
            # IF ALREADE HAVE EXTERNAL ID - JUST RETRIEVE THE ORDER
            # PASS EXTERNAL SILPO ORDER ID
            response = client.get_order(silpo_order["external_id"])
            internal_status = get_internal_status(response.status)

            print(
                f"Treaking for Silpo Order with HTTP GET /api/orders. Status: {internal_status}"
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
                cooked = True
                all_orders_cooked(order_id)


@celery_app.task(queue="high_priority")
def order_in_kfc(order_id: int, items):
    client = kfc.Client()
    cache = CacheService()
    restaurant = Restaurant.objects.get(name="KFC")

    def get_internal_status(status: str) -> OrderStatus:
        """Normalizes external status and maps it to internal.
        Supports variants: 'not started', 'not_started', 'Not-Started', etc.
        """
        if status is None:
            raise ValueError("External status is required")

        provider_key = "kfc"
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

    # GET TRACKING ORDER FROM THE CACHE
    tracking_order = TrackingOrder(**cache.get(namespace="orders", key=str(order_id)))

    response: kfc.OrderResponse = client.create_order(
        kfc.OrderRequestBody(
            order=[
                kfc.OrderItem(dish=item.dish.name, quantity=item.quantity)
                for item in items
            ]
        )
    )
    internal_status = get_internal_status(response.status)

    # UPDATE CACHE WITH EXTERNAL ID AND STATE
    tracking_order.restaurants[str(restaurant.pk)] |= {
        "external_ID": response.id,
        "status": internal_status,
    }

    print(f"Created KFC Order. External ID: {response.id}, Status: {internal_status}")
    cache.set(namespace="orders", key=str(order_id), value=asdict(tracking_order))

    # save another item form MAPPING to the Internal Order
    cache.set(
        namespace="kfc_orders",
        key=response.id,  # external KFC order id
        value={"internal_order_id": order_id},
    )


def schedule_order(order: Order):
    # define services and data state
    cache = CacheService()
    tracking_order = TrackingOrder()

    items_by_restaurants = order.items_by_restaurant()
    for restaurant, items in items_by_restaurants.items():
        # update traking order instance to be saved to the cache
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
                order_in_silpo.delay(order.pk, items)
                # or
                # order_in_silpo.apply_async()
            case "kfc":
                order_in_kfc.delay(order.pk, items)
            case _:
                raise ValueError(
                    f"Restaurant {restaurant.name} is not available for processing"
                )
