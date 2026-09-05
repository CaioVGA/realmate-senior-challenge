import logging

from django.db import transaction

from conversations.models import Conversation, Message, MessageRole
from conversations.payloads import IncomingMessage
from conversations.tasks import schedule_conversation_processing

logger = logging.getLogger(__name__)


def register_incoming_message(incoming: IncomingMessage) -> Message | None:
    """Persiste a mensagem do cliente e agenda o processamento. Devolve None se for duplicata."""
    with transaction.atomic():
        conversation, _ = Conversation.objects.get_or_create(user_phone=incoming.user_phone)
        message, created = Message.objects.get_or_create(
            external_id=incoming.message_id,
            defaults={
                "conversation": conversation,
                "role": MessageRole.CUSTOMER,
                "content": incoming.content,
                "timestamp": incoming.timestamp,
            },
        )
        if not created:
            logger.info("Mensagem %s já registrada, ignorando", incoming.message_id)
            return None

        conversation.register_activity(incoming.timestamp)
        transaction.on_commit(lambda: schedule_conversation_processing(conversation.pk, message.pk))

    return message
