import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db  # to work with database
def test_user_creation(api_client):
    request_body = {
        "email": "user@email.com",
        "password": "Pa$$w0rd",
        "phone_number": "+380990000000",
        "first_name": "New",
        "last_name": "User",
    }
    response = api_client.post(path="/users/", data=request_body)
    result = response.json()
    john = User.objects.get(id=result["id"])

    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.count() == 1
    assert john.first_name == result["first_name"]
    assert john.last_name == result["last_name"]


@pytest.mark.django_db
def test_authenticated_user_retrieve(api_client, user):
    api_client.force_authenticate(user=user)

    response = api_client.get(path="/users/")
    result = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result["email"] == user.email
    assert result["first_name"] == "Active"
    assert result["last_name"] == "User"


@pytest.mark.django_db
def test_unauthenticated_user_retrieve(api_client):
    response = api_client.get(path="/users/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_user_activation(api_client, inactive_user, mock_activation_service):
    mock_activation_service.activate_user.return_value = None
    mock_activation_service.remove_activation_key.return_value = None

    request_body = {"email": inactive_user.email, "key": str(uuid.uuid4())}
    response = api_client.post(path="/users/activate/", data=request_body)

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_user_activation_with_invalid_key(api_client, inactive_user, mock_activation_service):
    mock_activation_service.activate_user.side_effect = ValueError("No payload in cache")
    mock_activation_service.resend_activation_link.return_value = None

    request_body = {"email": inactive_user.email, "key": str(uuid.uuid4())}
    response = api_client.post(path="/users/activate/", data=request_body)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert (
        f"Key `{request_body["key"]}` does not exist. A new activation key has been sent to `{inactive_user.email}`"
        in response.data["detail"]
    )
    mock_activation_service.resend_activation_link.assert_called_once_with(inactive_user)


# class UserTestCase(TestCase):
#     def test_john_creation(self):
#         client = Client()
#         request_body = {
#             "email": "john@email.com",
#             "phone_number": "+380990000000",
#             "password": "Pa$$w0rd",
#             "first_name": "John",
#             "last_name": "Doe",
#         }

#         response = client.post(path="/users/", data=request_body)
#         result = response.json()

#         total_users = User.objects.count()
#         john = User.objects.get(id=result["id"])

#         assert response.status_code == status.HTTP_201_CREATED
#         assert total_users == 1
#         assert john.pk == result["id"]
#         assert john.first_name == result["first_name"]
#         assert john.last_name == result["last_name"]
#         assert john.role == result["role"]
