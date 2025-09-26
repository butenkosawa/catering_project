from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions")
    created_at = models.DateTimeField(auto_now_add=True)


class ChatMessage(models.Model):
    SYSTEM = "system"
    USER = "user"
    SENDER_CHOICES = [(SYSTEM, "System"), (USER, "User")]

    session = models.ForeignKey("ChatSession", on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self) -> str:
        return f"[{self.timestamp} {self.sender}: {self.content[:20]}]"
