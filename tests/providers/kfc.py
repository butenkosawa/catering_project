import asyncio
import httpx
import random
import time

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Literal

OrderStatus = Literal["not started", "cooking", "cooked", "finished"]
STORAGE: dict[str, OrderStatus] = {}
CATERING_API_WEBHOOK_URL = (
    "http://api:8000/webhooks/kfc/3d4d05d9-835e-433d-bb3b-e218bcbfa431/"
)

app = FastAPI(title="KFC API")


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
        print(f"KFC: [{order_id}] --> {status}")

        if status == "finished":
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(
                        CATERING_API_WEBHOOK_URL,
                        data={"id": order_id, "status": status},
                    )
                except httpx.ConnectError:
                    print("API connection failed")
                else:
                    print(f"KFC: {CATERING_API_WEBHOOK_URL} notified about {status}")


@app.post("/api/orders")
async def make_order(body: OrderRequestBody, background_tasks: BackgroundTasks):
    print(body)

    order_id = f"{int(time.time())}{random.randint(1000,9999)}"
    STORAGE[order_id] = "not started"
    background_tasks.add_task(update_order_status, order_id)

    return {"id": order_id, "status": "not started"}


@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    return STORAGE.get(order_id, {"error": "No such order"})
