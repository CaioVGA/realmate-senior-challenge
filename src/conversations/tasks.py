import logging

from celery import shared_task
from django.conf import settings

from assistant.runner import generate_reply
from conversations.models import Conversation, MessageRole
from conversations.services.history import conversation_turns
from conversations.services.replies import recommended_codes, store_assistant_reply

logger = logging.getLogger(__name__)


def schedule_conversation_processing(conversation_id: int, message_id: int) -> None:
    process_conversation.apply_async(
        (conversation_id, message_id),
        countdown=settings.MESSAGE_DEBOUNCE_SECONDS,
    )


@shared_task(name="conversations.tasks.process_conversation")
def process_conversation(conversation_id: int, trigger_message_id: int) -> None:
    """Responde a conversa se, após o debounce, a mensagem que agendou a execução ainda for a última."""
    conversation = Conversation.objects.filter(pk=conversation_id).first()
    if conversation is None:
        logger.warning("Conversa %s não encontrada", conversation_id)
        return

    last_customer_message = conversation.messages.filter(role=MessageRole.CUSTOMER).order_by("-id").first()
    if last_customer_message is None or last_customer_message.pk != trigger_message_id:
        logger.info("Processamento da mensagem %s descartado pelo debounce", trigger_message_id)
        return

    reply = generate_reply(conversation_turns(conversation), recommended_codes(conversation))
    store_assistant_reply(conversation, reply.content, reply.recommended_codes)
