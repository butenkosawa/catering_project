import enum
from dataclasses import dataclass, asdict

import httpx


class OrderStatus(enum.StrEnum):
    NOT_STARTED = "not_started"
    COOKING = "cooking"
    COOKED = "cooked"
    FINISHED = "finished"
