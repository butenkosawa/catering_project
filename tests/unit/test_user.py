import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class UserTestCase(TestCase):
    def test_john_creation(self):
        # setup input data
        payload = {
            "email": "john@email.com",
            "phone_number": "+380990000000",
            "password": "Pa$$w0rd",
            "first_name": "John",
            "last_name": "Doe",
        }

        # action
        User.objects.create(**payload)

        # evaulate
        john = User.objects.first()
        total_users = User.objects.count()

        self.assertEqual(total_users, 1)
        for attr, value in payload.items():
            if attr == "passwod":
                continue

            assert getattr(john, attr) == value


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "john@email.com", "password": "Pa$$w0rd", "phone_number": "+380991111111"},  # same email
        {"email": "marry@email.com", "password": "Pa$$w0rd", "phone_number": "+380990000000"},  # same phone number
    ],
)
def test_user_duplicate(john, django_user_model, payload):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            django_user_model.objects.create_user(**payload)
