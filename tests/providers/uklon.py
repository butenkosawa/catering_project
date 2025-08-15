import asyncio
import random
import uuid

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Literal

ORDER_STATUSES = ("not started", "delivery", "delivered")

STORAGE: dict[str, dict] = {}

app = FastAPI()


class OrderRequestBody(BaseModel):
    adresses: list[str] = Field(min_length=1)
    comments: list[str] = Field(min_length=1)


async def delivery(order_id):
    for _ in range(5):
        STORAGE[order_id]["location"] = (random.random(), random.random())

    for address in STORAGE[order_id]["addresses"]:
        await asyncio.sleep(1)
        for _ in range(5):
            STORAGE[order_id]["location"] = (random.random(), random.random())
            await asyncio.sleep(0.5)

        print(f"Delivered to {address}")


async def update_order_status(order_id):
    for status in ORDER_STATUSES[1:]:
        STORAGE[order_id]["location"] = (random.random(), random.random())
        await asyncio.sleep(random.randint(1, 2))

        if status == "delivery":
            await delivery(order_id)

        STORAGE[order_id]["status"] = status
        print(f"UKLON: [{order_id}] --> {status}")


@app.post("/drivers/orders")
async def make_order(body: OrderRequestBody, background_tasks: BackgroundTasks):
    print(body)
    order_id = str(uuid.uuid4())
    STORAGE[order_id] = {
        "id": order_id,
        "status": "not started",
        "addresses": body.adresses,
        "comments": body.comments,
        "location": (random.random(), random.random()),
    }
    background_tasks.add_task(update_order_status, order_id)

    return STORAGE.get(order_id, {"error": "No such order"})


@app.get("/drivers/orders/{order_id}")
async def get_order(order_id: str):
    return STORAGE.get(order_id, {"error": "No such order"})
