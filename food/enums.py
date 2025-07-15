import enum


class OrderStatus(enum.StrEnum):
    NOT_STARTED = enum.auto()
    COOKING_REJECTED = enum.auto()
    COOKING = enum.auto()
    COOKED = enum.auto()
    DELIVERY_LOOKUP = enum.auto()
    DELIVERY = enum.auto()
    DELIVERED = enum.auto()
    NOT_DELIVERED = enum.auto()
    CANCELLED_BY_CUSTOMER = enum.auto()
    CANCELLED_BY_MANAGER = enum.auto()
    CANCELLED_BY_ADMIN = enum.auto()
    CANCELLED_BY_RESTAURANT = enum.auto()
    CANCELLED_BY_DRIVER = enum.auto()
    FAILED = enum.auto()

    @classmethod
    def choices(cls):
        """
        Pair example:
        (not_started, Not_started)
        """

        results = []

        for element in cls:
            _element = (
                element.value,
                element.name.replace("_", " ").lower().capitalize(),
            )
            results.append(_element)

        return results


class DeliveryProvider(enum.StrEnum):
    UKLON = enum.auto()
    UBER = enum.auto()
