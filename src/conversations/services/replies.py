import logging
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from conversations.models import Conversation, Message, MessageRole, Recommendation
from properties.models import Property

logger = logging.getLogger(__name__)


def recommended_codes(conversation: Conversation) -> list[str]:
    return list(
        Recommendation.objects.filter(conversation=conversation)
        .order_by("created_at", "id")
        .values_list("property__code", flat=True)
    )


def store_assistant_reply(
    conversation: Conversation,
    content: str,
    property_codes: Sequence[str] = (),
) -> Message:
    """Persiste a resposta da IA e registra, de forma idempotente, os imóveis recomendados."""
    with transaction.atomic():
        moment = _reply_moment(conversation)
        message = Message.objects.create(
            conversation=conversation,
            external_id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=content,
            timestamp=moment,
        )
        _register_recommendations(conversation, property_codes)
        conversation.register_activity(moment)
    return message


def _reply_moment(conversation: Conversation) -> datetime:
    """O timestamp do cliente vem de um sistema externo e pode estar à frente do relógio local.

    A API de histórico exige ordem cronológica, então a resposta nunca pode ficar antes da mensagem
    que ela responde.
    """
    now = timezone.now()
    last = conversation.last_message_at
    return now if last is None or last < now else last + timedelta(seconds=1)


def _register_recommendations(conversation: Conversation, property_codes: Sequence[str]) -> None:
    if not property_codes:
        return
    listings = {listing.code: listing for listing in Property.objects.filter(code__in=property_codes)}
    Recommendation.objects.bulk_create(
        [
            Recommendation(conversation=conversation, property=listings[code])
            for code in property_codes
            if code in listings
        ],
        ignore_conflicts=True,
    )
