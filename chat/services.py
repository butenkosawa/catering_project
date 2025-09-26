import datetime
import json
from datetime import date

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from food.models import Dish
from food.serializers import OrderItemSerializer
from shared.cache import CacheService
from shared.llm import LLMService
from users.models import User

from .models import ChatMessage, ChatSession

CACHE_NAMESPACE = "chat_order_creation"


class OrderInCacheSerializer(serializers.Serializer):
    items = OrderItemSerializer(many=True, required=False)
    eta = serializers.DateField(required=False)
    delivery_provider = serializers.CharField(default="uber", required=False)


class ChatConversationManager:
    def __init__(self, user) -> None:
        self.user: User = user
        self.llm: LLMService = LLMService()
        self.cache: CacheService = CacheService()
        self.session: ChatSession | None = None

    def get_or_create_session(self, session_id: int | None = None) -> ChatSession:
        if session_id is not None:
            self.session = get_object_or_404(ChatSession, pk=session_id, user=self.user)
        else:
            self.session = ChatSession.objects.create(user=self.user)

        return self.session

    def add_user_message(self, content: str) -> ChatMessage:
        if self.session is None:
            raise ValueError("Session must be initialized before adding messages")
        return ChatMessage.objects.create(session=self.session, sender=ChatMessage.USER, content=content)

    def add_system_message(self, content: str) -> ChatMessage:
        if self.session is None:
            raise ValueError("Session must be initialized before adding messages")
        return ChatMessage.objects.create(session=self.session, sender=ChatMessage.SYSTEM, content=content)

    def build_prompt(self, messages: QuerySet[ChatMessage], missing_fields: list[str] | None = None) -> str:
        avaliable_dishes_info = self._get_avaliable_dishes_info()
        order_data = self._load_order_data()
        required_order_create_fields = OrderInCacheSerializer._declared_fields.keys()

        msgs = "\n".join(f"{msg.sender}: '{msg.content}'" for msg in messages)
        prompt = "\n".join(
            [
                "You are assistant for the Catering Application",
                "Your task is to extract information about user's order,"
                "based on user's conversation with AI Assistant",
                "Here is the list of avaliable dishes with their prices and IDs:",
                avaliable_dishes_info,
                "\nBelow you can see the history of the conversation:",
                msgs,
                "\nCurrently we have the next data in the cache about about the current conversation and order:",
                str(order_data),
                "\nYou task is to analyze existing item and what fields are missing.",
                f"The list of required fields to create an order is next: {required_order_create_fields}",
                "Now create a message, based on the conversation history, that is going to make a user tell you",
                "more information about missing fields, so we can parse them out!",
                "You have to respond like a real human with accent and other things.",
                "The data, provided to you is only for additional context. Just talk like a real.",
                "If all the fields are - Please ask user again if the order is correct!",
            ]
        )

        return prompt

    def process_message(self, user_message: str) -> dict:
        # User Prompt: Hello, can I make an order?
        self.add_user_message(user_message)
        self._update_cache_order_from_last_message(user_message)

        if self.session is None:
            raise ValueError("Session must be initialized before processing messages")

        # Instead of naive extraction, trust LLM to pase user message + dish list
        messages = self.session.messages.all()
        prompt = self.build_prompt(messages)
        # Inference: Yes, bla, bla, bla
        llm_response = self.llm.ask(prompt)

        # Assume LLM's response either confirms order or asks for missing info
        # Backend parses LLM response or relies on explicit user confirmation in next message

        self.add_system_message(llm_response)

        # TODO: Order Creating  Logic if confirmation detected, etc...

        return {"session_id": self.session.pk, "sender": ChatMessage.SYSTEM, "content": llm_response}

    @property
    def _cache_key(self) -> str:
        if self.session is None:
            raise ValueError("Session must be initialized before processing messages")
        return str(self.session.pk)

    def _load_order_data(self) -> dict:
        data = self.cache.get(namespace=CACHE_NAMESPACE, key=self._cache_key)
        return data or {}

    def _save_order_data(self, order_data: dict):
        if "items" in order_data:
            for item in order_data["items"]:
                if isinstance(item["dish"], Dish):
                    item["dish"] = item["dish"].pk

        if "eta" in order_data and isinstance(order_data["eta"], datetime.date):
            order_data["eta"] = order_data["eta"].isoformat()

        self.cache.set(namespace=CACHE_NAMESPACE, key=self._cache_key, value=order_data, ttl=3600)

    def _get_avaliable_dishes_info(self) -> str:
        dishes: QuerySet[Dish] = Dish.objects.all()

        # Format dishes for prompt
        return "\n".join(f"{dish.pk}: {dish.name} ({dish.price})" for dish in dishes)

    def _update_cache_order_from_last_message(self, message: str) -> None:
        """
        (1) Fetch order data from the CACHE
        (2) Put message with object from the CACHE to the LLM and ask to update
        """

        order_from_cache: dict = self._load_order_data()
        dishes: str = self._get_avaliable_dishes_info()

        new_order_payload_prompt = f"""
        You are assistant in Catering Application.
        Your task is to parse existing order items python dictionary and update it
        according to new user data.

        The new user message comes from the chat with AI and you only have to update the
        existing order by putting new items or removing existing items or updating the ETA.

        The cache entry structure has next fields:
        - 'eta': timestamp string,
        - 'items': list[dict]
            - "dish": id of an avaliable dish
            - "quantity": amount of dish to order
        - "delivery_provider": always "uber"

        The Existing Order Data from the CACHE is below:
        {order_from_cache}

        Avaliable Dishes are below:
        {dishes}

        Today is {date.today()}

        Now provide me new order structure, in exactly the same way so I can load it with
        `json.loads()` function from python. No markdown, no other verbosity. Only plain text
        which is a valid JSON for loading.

        If the order can NOT be changed with the latest message - say NO CHANGES

        User's last message:
        {message}
        """

        inference: str = self.llm.ask(new_order_payload_prompt)

        print(new_order_payload_prompt)
        print("\n\n")
        print(inference)
        print("\n\n")

        # skip if no changes at all
        if "no changes" in inference.lower():
            return

        new_order_data = json.loads(inference)
        serializer = OrderInCacheSerializer(data=new_order_data)
        serializer.is_valid(raise_exception=True)
        self._save_order_data(serializer.validated_data)
