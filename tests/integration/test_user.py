from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.client import Client
from rest_framework import status

User = get_user_model()


class UserTestCase(TestCase):
    def test_john_creation(self):
        client = Client()
        request_body = {
            "email": "john@email.com",
            "phone_number": "+380990000000",
            "password": "Pa$$w0rd",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = client.post(path="/users/", data=request_body)
        result = response.json()

        total_users = User.objects.count()
        john = User.objects.get(id=result["id"])

        assert response.status_code == status.HTTP_201_CREATED
        assert total_users == 1
        assert john.pk == result["id"]
        assert john.first_name == result["first_name"]
        assert john.last_name == result["last_name"]
        assert john.role == result["role"]
