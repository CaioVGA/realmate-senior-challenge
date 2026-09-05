from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

MESSAGE_RECEIVED = "MESSAGE_RECEIVED"


class WebhookPayloadError(ValueError):
    """Payload do webhook fora do contrato esperado."""


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    message_id: str
    user_phone: str
    content: str
    timestamp: datetime


def parse_incoming_message(content: Mapping[str, object]) -> IncomingMessage:
    return IncomingMessage(
        message_id=_required_text(content, "message_id"),
        user_phone=_required_text(content, "user_phone_number"),
        content=_required_text(content, "message_content"),
        timestamp=_parse_timestamp(_required_text(content, "timestamp")),
    )


def _required_text(content: Mapping[str, object], field: str) -> str:
    value = content.get(field)
    if not isinstance(value, str) or not value.strip():
        raise WebhookPayloadError(f"campo obrigatório ausente ou inválido: {field}")
    return value.strip()


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise WebhookPayloadError(f"timestamp inválido: {value!r}") from error
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
