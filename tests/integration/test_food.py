from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from food.models import Dish, Order, OrderItem, Restaurant

User = get_user_model()


# ===========================
# DISHES
# ===========================
class DishesAPITestCase(TestCase):
    # def tearDown(self) -> None:
    #     return super().tearDown()

    def setUp(self) -> None:
        self.anonymous = APIClient()
        self.client = APIClient()

        self.john = User.objects.create_user(email="john@email.com", password="Pa$$w0rd")
        self.john.is_active = True
        self.john.save()

        # JWT Token claim
        response = self.client.post(
            reverse("obtain_token"),
            {
                "email": "john@email.com",
                "password": "Pa$$w0rd",
            },
        )

        assert response.status_code == status.HTTP_200_OK, response.json()
        token = response.data["access"]

        # set the JWT token in the Authorization HTTP Header
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Populate Data
        self.rest1 = Restaurant.objects.create(name="MamaPizza", address="123 Main St")
        self.rest2 = Restaurant.objects.create(name="Dominos", address="13 Black St")

        self.dish1 = Dish.objects.create(restaurant=self.rest1, name="Dish1", price=100)
        self.dish2 = Dish.objects.create(restaurant=self.rest1, name="Dish2", price=150)

        self.dish3 = Dish.objects.create(restaurant=self.rest2, name="Dish3", price=200)
        self.dish4 = Dish.objects.create(restaurant=self.rest2, name="Dish4", price=250)

    def test_get_dishes_anonymous(self):
        response = self.anonymous.get(reverse("food-dishes-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert type(response.json()) is not list

    def test_get_dishes_authorized(self):
        response = self.client.get(reverse("food-dishes-list"))
        restaurants = response.json()

        total_restaurants = len(restaurants)
        total_dishes = 0
        for rest in restaurants:
            total_dishes += len(rest["dishes"])

        assert response.status_code == status.HTTP_200_OK
        assert total_restaurants == 2
        assert total_dishes == 4


@pytest.mark.django_db
def test_create_dish_as_admin(api_client, admin, restaurant):
    api_client.force_authenticate(user=admin)
    request_body = {"name": "TestDish", "price": 100, "restaurant": restaurant.pk}
    response = api_client.post(path="/food/dishes/", data=request_body, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "TestDish"
    assert response.data["price"] == 100
    assert Dish.objects.filter(name="TestDish").exists()


@pytest.mark.django_db
def test_create_dish_as_user(api_client, user, restaurant):
    api_client.force_authenticate(user=user)
    request_body = {"name": "TestDish", "price": 100, "restaurant": restaurant.pk}
    response = api_client.post(path="/food/dishes/", data=request_body, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["detail"] == "You do not have permission to perform this action."


# ===========================
# ORDERS
# ===========================
@pytest.mark.django_db
def test_create_order(api_client, user, dish, mocker):
    mock_schedule_order = mocker.patch("food.views.schedule_order")
    api_client.force_authenticate(user=user)

    request_body = {
        "eta": str((datetime.now() + timedelta(days=1)).date()),
        "delivery_provider": "uber",
        "items": [{"dish": dish.pk, "quantity": 3}],
    }

    response = api_client.post(path="/food/orders/", data=request_body, format="json")

    assert response.status_code == status.HTTP_201_CREATED

    order = Order.objects.get()
    assert order.user == user
    assert order.total == 3 * dish.price

    items = OrderItem.objects.filter(order=order)
    assert items.count() == 1

    mock_schedule_order.assert_called_once()
    args, kwargs = mock_schedule_order.call_args
    assert args[0].id == order.pk


@pytest.mark.django_db
def test_retrieve_order(api_client, user, dish):
    api_client.force_authenticate(user=user)
    order = Order.objects.create(
        user=user, delivery_provider="Uklon", eta=str((datetime.now() + timedelta(days=1)).date()), total=100
    )
    OrderItem.objects.create(order=order, dish=dish, quantity=1)
    response = api_client.get(path=f"/food/orders/{order.pk}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == order.pk
    assert response.data["items"][0]["dish"] == dish.pk


# ===========================
# IMPORT DISHES
# ===========================
@pytest.mark.django_db
def test_import_dishes_success(client, admin, restaurant):
    client.force_login(user=admin)
    csv_content = f"name,price,restaurant\nTestDish,50,{restaurant.name}\n"
    file = SimpleUploadedFile("dishes.csv", csv_content.encode("utf-8"), content_type="text/csv")
    response = client.post(path=reverse("import_dishes"), data={"file": file})

    assert response.status_code == status.HTTP_302_FOUND or response.status_code == status.HTTP_200_OK
    dish = Dish.objects.get(name="TestDish")
    assert dish.price == 50
    assert dish.restaurant == restaurant


@pytest.mark.django_db
def test_import_dishes_invalid_method(client):
    with pytest.raises(ValueError):
        client.get(path=reverse("import_dishes"))
