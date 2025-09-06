import pytest
from rest_framework.test import APIClient

from food.models import Dish, Restaurant
from users.models import Role, User


@pytest.fixture(autouse=True)
def api_client():
    return APIClient()


@pytest.fixture
def admin(django_user_model) -> User:
    user = django_user_model.objects.create_superuser(
        email="admin@email.com",
        password="Pa$$w0rd",
        phone_number="+380999999999",
        first_name="Admin",
        last_name="User",
        is_superuser=True,
    )
    user.role = Role.ADMIN
    user.save(update_fields=["role"])

    return user


@pytest.fixture
def user(django_user_model) -> User:
    return django_user_model.objects.create_user(
        email="active_user@email.com",
        password="Pa$$w0rd",
        phone_number="+380990000001",
        first_name="Active",
        last_name="User",
        is_active=True,
    )


@pytest.fixture
def inactive_user(django_user_model) -> User:
    return django_user_model.objects.create_user(
        email="inactive_user@email.com",
        password="Pa$$w0rd",
        phone_number="+380990000000",
        first_name="Inactive",
        last_name="User",
        is_active=False,
    )


@pytest.fixture
def restaurant(db):
    return Restaurant.objects.create(name="KFC", address="Street 1")


@pytest.fixture
def dish(restaurant):
    return Dish.objects.create(restaurant=restaurant, name="Soup", price=100)


@pytest.fixture
def mock_activation_service(mocker):
    mock_service = mocker.patch("users.views.ActivationService")
    return mock_service.return_value
