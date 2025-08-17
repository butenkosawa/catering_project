import asyncio
import random
import uuid

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Literal

OrderStatus = Literal["not started", "cooking", "cooked", "finished"]

STORAGE: dict[str, OrderStatus] = {}
"""
{
    "880cc42b-0577-42c5-8247-1e29f673df54": "not_started"
}
"""

app = FastAPI()


class OrderItem(BaseModel):
    dish: str
    quantity: int


class OrderRequestBody(BaseModel):
    order: list[OrderItem]


async def update_order_status(order_id):
    ORDER_STATUSES = ("cooking", "cooked", "finished")
    for status in ORDER_STATUSES:
        await asyncio.sleep(random.randint(4, 6))
        STORAGE[order_id] = status
        print(f"SILPO: [{order_id}] --> {status}")


@app.post("/api/orders")
async def make_order(body: OrderRequestBody, background_tasks: BackgroundTasks):
    print(body)

    order_id = str(uuid.uuid4())
    STORAGE[order_id] = "not_started"
    background_tasks.add_task(update_order_status, order_id)

    return {"id": order_id, "status": "not started"}


@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    return {"id": order_id, "status": STORAGE.get(order_id)}
