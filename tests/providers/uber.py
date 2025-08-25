import asyncio
import random
import uuid

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

ORDER_STATUSES = ("not started", "delivery", "delivered")
STORAGE: dict[str, dict] = {}

CATERING_API_WEBHOOK_URL = "http://api:8000/webhooks/uber/e7a684e0-03e3-46ba-97eb-f3604abc494c/"

app = FastAPI(title="Uber API")


class OrderRequestBody(BaseModel):
    addresses: list[str] = Field(min_length=1)
    comments: list[str] = Field(min_length=1)


async def delivery(order_id):
    while True:
        await asyncio.sleep(1)
        STORAGE[order_id]["location"] = (random.random(), random.random())

        status = STORAGE[order_id]["status"]
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    CATERING_API_WEBHOOK_URL,
                    data={
                        "id": order_id,
                        "status": status,
                        "location": STORAGE[order_id]["location"],
                    },
                )
                print(f"UBER: [{status}]: 📍 {STORAGE[order_id]["location"]}")
            except httpx.ConnectError:
                print("API connection failed")

        if status == "delivered":
            print(f"🏁 Delivered to {STORAGE[order_id]["location"]}")
            break


async def update_order_status(order_id):
    for status in ORDER_STATUSES[1:]:
        await asyncio.sleep(random.randint(5, 8))
        STORAGE[order_id]["status"] = status
        print(f"UBER: [{order_id}] status changed to {status}")


@app.post("/drivers/orders")
async def make_order(body: OrderRequestBody):
    print(body)
    order_id = str(uuid.uuid4())
    STORAGE[order_id] = {
        "id": order_id,
        "status": "not started",
        "addresses": body.addresses,
        "comments": body.comments,
        "location": (random.random(), random.random()),
    }

    asyncio.create_task(delivery(order_id))
    asyncio.create_task(update_order_status(order_id))

    return STORAGE.get(order_id, {"error": "No such order"})


@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    return STORAGE.get(order_id, {"error": "No such order"})
