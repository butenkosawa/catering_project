from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from food.models import Dish, Restaurant

User = get_user_model()


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
