from datetime import datetime
from typing import TYPE_CHECKING

from django.core.validators import RegexValidator
from django.db import models

from properties.models import Property

phone_validator = RegexValidator(
    regex=r"^\+\d{12,15}$",
    message="O telefone deve seguir o formato +5588999999999.",
)


class ConversationStatus(models.TextChoices):
    ACTIVE = "active", "Ativa"
    CLOSED = "closed", "Encerrada"


class MessageRole(models.TextChoices):
    CUSTOMER = "customer", "Cliente"
    ASSISTANT = "assistant", "Assistente"


class Conversation(models.Model):
    if TYPE_CHECKING:
        messages: models.Manager["Message"]

    user_phone = models.CharField(max_length=20, unique=True, validators=[phone_validator])
    status = models.CharField(
        max_length=16,
        choices=ConversationStatus.choices,
        default=ConversationStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-last_message_at",)

    def __str__(self) -> str:
        return self.user_phone

    def register_activity(self, moment: datetime) -> None:
        if self.last_message_at is None or self.last_message_at < moment:
            self.last_message_at = moment
            self.save(update_fields=["last_message_at"])


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    external_id = models.CharField(max_length=64, unique=True)
    role = models.CharField(max_length=16, choices=MessageRole.choices)
    content = models.TextField()
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("timestamp", "id")
        indexes = [models.Index(fields=["conversation", "timestamp"])]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:40]}"


class Recommendation(models.Model):
    conversation = models.ForeignKey(Conversation, related_name="recommendations", on_delete=models.CASCADE)
    property = models.ForeignKey(Property, related_name="recommendations", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(fields=["conversation", "property"], name="unique_recommendation_per_conversation")
        ]

    def __str__(self) -> str:
        return f"{self.conversation.user_phone} -> {self.property.code}"
