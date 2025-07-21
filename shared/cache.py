"""
Structure:
    set(key: str, value: str)
    get(key: str)
    delete(key: str)
"""

# from dataclasses import asdict, dataclass
import redis
import json
from typing import Any


# @dataclass
# class Structure:
#     id: int
#     name: str


class CacheService:
    """
    set(namespace='user_activation', key=12, value=Activation(...))
    get(namespace='user_activation', key=12) -> Activation(...)
    """

    def __init__(self) -> None:
        self.connection: redis.Redis = redis.Redis.from_url("redis://localhost:6379/0")

    @staticmethod
    def _build_key(namespace: str, key: str) -> str:
        return f"{namespace}: {key}"

    def set(self, namespace: str, key: str, value: dict, ttl: int | None = None):
        # if not isinstance(value, Structure):
        #     payload = asdict(value)

        self.connection.set(
            name=self._build_key(namespace, key), value=json.dumps(value), ex=ttl
        )

    def get(self, namespace: str, key: str):
        result: str = self.connection.get(self._build_key(namespace, key))  # type: ignore

        return json.loads(result)

    def delete(self, namespace: str, key: str): ...
