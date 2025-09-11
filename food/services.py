from dataclasses import asdict, dataclass, field
from time import sleep

from config import celery_app
from config.settings import CACHE_TTL
from shared.cache import CacheService
from shared.llm import LLMService
from users.models import Role, User

from .enums import OrderStatus
from .mapper import RESTAURANT_EXTERNAL_TO_INTERNAL
from .models import Dish, Order, Restaurant
from .providers import kfc, silpo, uber, uklon
from .serializers import DishSerializer, OrderSerializer


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
                status: NOT STARTED, DELIVERY, DELIVERED
            }
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
        print(f"Unknown external status for {provider_key}: {status!r}. Known keys: {list(mapping.keys())}")
        raise ValueError(f"Unknown external status '{status}' for provider '{provider_key}'")

    return internal


def all_orders_cooked(order_id: int):
    tracking_order = get_tracking_order(order_id)

    print(f"Checking if all orders are cooked: {tracking_order.restaurants}")

    if all((payload["status"] == OrderStatus.COOKED for _, payload in tracking_order.restaurants.items())):
        Order.objects.filter(id=order_id).update(status=OrderStatus.COOKED)
        print("✅ All orders are COOKED")

        # Start orders delivery
        order_delivery.delay(order_id)
    else:
        print(f"Not all orders are cooked: {tracking_order=}")


@celery_app.task(queue="low_priority")
def order_delivery(order_id: int):
    """Using random provider (or now only Uklon) - start processing delivery order."""

    def delivery_by_uklon(order: Order, addresses: list[str], comments: list[str]):
        provider = uklon.Client()

        _response: uklon.OrderResponse = provider.create_order(
            uklon.OrderRequestBody(addresses=addresses, comments=comments)
        )

        tracking_order = get_tracking_order(order.pk)
        tracking_order.delivery["status"] = OrderStatus.DELIVERY
        tracking_order.delivery["location"] = _response.location

        current_status: uklon.OrderStatus = _response.status

        while current_status != uklon.OrderStatus.DELIVERED:
            response = provider.get_order(_response.id)

            print(f"🚙 Uklon [{response.status}]: 📍 {response.location}")

            if current_status == response.status:
                sleep(1)
                continue

            current_status = response.status  # DELIVERY, DELIVERED

            tracking_order.delivery["location"] = response.location

            # update cache
            cache.set(
                "orders",
                str(order.pk),
                asdict(tracking_order),
                ttl=CACHE_TTL["ORDER_DATA"],
            )

        print(f"🏁 UKLON [{response.status}]: 📍 {response.location}")

        # update storage
        Order.objects.filter(id=order.pk).update(status=OrderStatus.DELIVERED)

        # update the cache
        tracking_order.delivery["status"] = OrderStatus.DELIVERED
        cache.set(
            namespace="orders",
            key=str(order.pk),
            value=asdict(tracking_order),
            ttl=CACHE_TTL["ORDER_DATA"],
        )

    def delivery_by_uber(order: Order, addresses: list[str], comments: list[str]):
        provider = uber.Client()

        response: uber.OrderResponse = provider.create_order(
            uber.OrderRequestBody(addresses=addresses, comments=comments)
        )

        # save another item form Mapping to the Internal Order
        cache.set(
            namespace="uber_orders",
            key=response.id,  # external UBER order id
            value={
                "internal_order_id": order.pk,
            },
            ttl=CACHE_TTL["EXTERNAL_ORDER_DATA"],
        )

    print("🚚 DELIVERY PROCESSING STARTED")

    cache = CacheService()
    order = Order.objects.get(id=order_id)

    # update Order state
    order.status = OrderStatus.DELIVERY_LOOKUP
    order.save()

    # prepare data for the first request
    addresses: list[str] = []
    comments: list[str] = []

    for rest_name, address in order.delivery_meta():
        addresses.append(address)
        comments.append(f"Delivery to the {rest_name}")

    if not order.delivery_provider:
        raise ValueError("Delivery provider is not set for this order")

    try:
        match order.delivery_provider.lower():
            case "uklon":
                order.status = OrderStatus.DELIVERY
                order.save()
                delivery_by_uklon(order=order, addresses=addresses, comments=comments)
            case "uber":
                order.status = OrderStatus.DELIVERY
                order.save()
                delivery_by_uber(order=order, addresses=addresses, comments=comments)
            case _:
                raise ValueError(f"Delivery provider {order.delivery_provider} is not available for processing")
    except ValueError as err:
        print(err)
    else:
        print(f"✅ DONE with Delivery: Order [{order.pk}] | Provider [{order.delivery_provider}]")


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
                    order=[silpo.OrderItem(dish=item.dish.name, quantity=item.quantity) for item in items]
                )
            )
            internal_status: OrderStatus = get_internal_status(provider_key="silpo", status=response.status)
            # UPDATE CACHE WITH EXTERNAL ID STATUS
            tracking_order.restaurants[str(restaurant.pk)] = {
                "external_id": response.id,
                "status": internal_status,
            }
            cache.set(
                namespace="orders",
                key=str(order_id),
                value=asdict(tracking_order),
                ttl=CACHE_TTL["ORDER_DATA"],
            )
        else:
            # IF ALREADY HAVE EXTERNAL ID - JUST RETRIEVE THE ORDER
            # PASS EXTERNAL SILPO ORDER ID
            response = client.get_order(silpo_order["external_id"])
            internal_status = get_internal_status(provider_key="silpo", status=response.status)
            print(f"Tracking for Silpo Order with HTTP GET /api/orders. Status: {internal_status}")

            if silpo_order["status"] != internal_status:
                tracking_order.restaurants[str(restaurant.pk)]["status"] = internal_status
                print(f"Silpo order status changed to {internal_status}")
                cache.set(
                    namespace="orders",
                    key=str(order_id),
                    value=asdict(tracking_order),
                    ttl=CACHE_TTL["ORDER_DATA"],
                )
                # if started cooking
                if internal_status == OrderStatus.COOKING:
                    Order.objects.filter(id=order_id).update(status=OrderStatus.COOKING)

            if internal_status == OrderStatus.COOKED:
                cooked = True
                all_orders_cooked(order_id)


@celery_app.task(queue="low_priority")
def order_in_kfc(order_id: int, items):
    client = kfc.Client()
    cache = CacheService()
    restaurant = Restaurant.objects.get(name="KFC")

    # GET TRACKING ORDER FROM THE CACHE
    tracking_order = get_tracking_order(order_id)

    response: kfc.OrderResponse = client.create_order(
        kfc.OrderRequestBody(order=[kfc.OrderItem(dish=item.dish.name, quantity=item.quantity) for item in items])
    )
    internal_status = get_internal_status(provider_key="kfc", status=response.status)

    # UPDATE CACHE WITH EXTERNAL ID AND STATE
    tracking_order.restaurants[str(restaurant.pk)] = {
        "external_ID": response.id,
        "status": internal_status,
    }

    print(f"Created KFC Order. External ID: {response.id}, Status: {internal_status}")
    cache.set(
        namespace="orders",
        key=str(order_id),
        value=asdict(tracking_order),
        ttl=CACHE_TTL["ORDER_DATA"],
    )

    # save another item form Mapping to the Internal Order
    cache.set(
        namespace="kfc_orders",
        key=response.id,  # external KFC order id
        value={
            "internal_order_id": order_id,
        },
        ttl=CACHE_TTL["EXTERNAL_ORDER_DATA"],
    )


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
    cache.set(
        namespace="orders",
        key=str(order.pk),
        value=asdict(tracking_order),
        ttl=CACHE_TTL["ORDER_DATA"],
    )

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
                raise ValueError(f"Restaurant {restaurant.name} is not available for processing")


def get_food_recommendations(user_id: int) -> dict:
    cache = CacheService()
    items = cache.get(namespace="recommendations", key=str(user_id))
    serialiser = DishSerializer(items["dishes"] if items else [], many=True)

    return {"recommendations": [serialiser.data]}


@celery_app.task(queue="low_priority")
def generate_recommendations():
    """Generate recommendations for each user in the system and put them to the cache."""

    # (1) setup (define initial instances)
    LIMIT_ORDERS = 5
    RECOMMENDATION_THRESHOLD = 2
    users = User.objects.filter(role=Role.CUSTOMER)
    llm = LLMService()
    cache = CacheService()

    # (2) for each user
    for user in users:
        # (3) get last orders
        print(f"✨ Checking orders for {user.email}")
        last_orders = user.orders.filter(status=OrderStatus.DELIVERED).order_by("-id")[:LIMIT_ORDERS]
        order_serializer = OrderSerializer(last_orders, many=True)

        print("=======================")
        print(order_serializer.data)
        print("=======================")

        # (4) build promt to get top dishes
        prompt = f"""
        Below you can see the list of orders:
        {order_serializer.data}

        Return me up to {RECOMMENDATION_THRESHOLD} top dishes according to this list.
        Return it without any verbosity except of coma separated ids.

        The response will be used in Python to split data by coma and
        convert to the integer all the ids.
        """

        # (5) LLM inference
        response = llm.ask(prompt)
        print(f"✨ LLM Result: {response}")

        # (6.1) validate dishes have valid ids
        try:
            dishes_ids: list[int] = [int(dish_id) for dish_id in response.split(",")]
        except ValueError as error:
            raise ValueError(f"LLM return invalid IDs for dishes: {response}") from error

        # (6.2) validate dishes ids exist (llm can hallucinate)
        dishes = Dish.objects.filter(id__in=dishes_ids)
        if dishes.count() != len(dishes_ids):
            raise ValueError("Some of returned dishes are not in the database")

        # (7) Build recommendations for the specific user in the cache
        serializer = DishSerializer(dishes, many=True)
        value = {"dishes": serializer.data}
        cache.set(namespace="recommendations", key=str(user.pk), value=value)
        print(f"✅ Data saved to the cache: {value}")
