import uuid

from django.core.mail import send_mail

from config import celery_app
from config.settings import CACHE_TTL
from shared.cache import CacheService

from .models import User


class ActivationService:
    UUID_NAMESPACE = uuid.uuid4()

    def __init__(self, email: str | None = None) -> None:
        self.email: str | None = email
        self.cache: CacheService = CacheService()

    def create_activation_key(self):
        # whether
        # key = uuid.uuid3(self.UUID_NAMESPACE, self.email)
        # or
        return uuid.uuid4()

    def save_activation_information(self, user_id: int, activation_key: str):
        """Save activation data to the cache.
        1. Connect to the Cache Service
        2. Save structure to the Cache:
        {
            "4b37cd21-0d7e-4e83-a97b-2aa0b04ff61f": {
                "user_id": 3
            }
        }
        3. Return `None`
        """
        self.cache.set(
            namespace="activation",
            key=activation_key,
            value={"user_id": user_id},
            ttl=CACHE_TTL["ACTIVATION"],
        )

        return None

    def send_user_activation_email(self, activation_key: str):
        # SMTP Client Send Email Request
        if self.email is None:
            raise ValueError("No email specified for user activation process")

        activation_link = f"https://frontend.catering.com/activation/{activation_key}"
        send_mail(
            subject="User Activation",
            message=f"Please, activate your account: {activation_link} ",
            from_email="admin@catering.com",
            recipient_list=[self.email],
        )

    def activate_user(self, activation_key: str):
        user_cache_payload: dict | None = self.cache.get(
            namespace="activation",
            key=activation_key,
        )

        if user_cache_payload is None:
            raise ValueError("No payload in cache")

        user = User.objects.get(id=user_cache_payload["user_id"])
        user.is_active = True
        user.save()

        # or for instance
        # User.objects.filter(id=user...).update(is_active=True)

    def resend_activation_link(self, user: User) -> None:
        """Send user activation link to specified email"""

        if self.email is None:
            raise ValueError("No email specified for user activation process")

        activation_key = self.create_activation_key()
        self.save_activation_information(
            user_id=user.id, activation_key=str(activation_key)
        )
        send_email.delay(email=self.email, activation_key=str(activation_key))

    def remove_activation_key(self, activation_key: str) -> None:
        """Remove activation key from the cache"""

        self.cache.delete(
            namespace="activation",
            key=activation_key,
        )


@celery_app.task(queue="low_priority")
def send_email(email: str, activation_key: str):
    service = ActivationService(email=email)
    print(f"SENDING ACTIVATION LINK TO: {email!r}")
    service.send_user_activation_email(activation_key)
