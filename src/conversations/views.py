import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from conversations.models import Conversation, Message
from conversations.payloads import MESSAGE_RECEIVED, WebhookPayloadError, parse_incoming_message
from conversations.services.ingestion import register_incoming_message
from conversations.services.replies import recommended_codes

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def message_webhook(request: HttpRequest) -> HttpResponse:
    try:
        payload: object = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "payload inválido"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "payload inválido"}, status=400)

    raw_content = payload.get("content")
    content: Mapping[str, object] = raw_content if isinstance(raw_content, dict) else {}
    message_id = content.get("message_id")

    if payload.get("event") != MESSAGE_RECEIVED:
        return JsonResponse({"status": "ignored", "message_id": message_id})

    try:
        incoming = parse_incoming_message(content)
    except WebhookPayloadError as error:
        logger.warning("Webhook rejeitado: %s", error)
        return JsonResponse({"error": str(error)}, status=400)

    if register_incoming_message(incoming) is None:
        return JsonResponse({"status": "ignored", "message_id": incoming.message_id})
    return JsonResponse({"status": "accepted", "message_id": incoming.message_id})


@require_GET
def conversation_messages(request: HttpRequest, user_phone: str) -> HttpResponse:
    conversation = Conversation.objects.filter(user_phone=user_phone).first()
    if conversation is None:
        return JsonResponse({"error": "conversa não encontrada"}, status=404)

    return JsonResponse(
        {
            "user_phone": conversation.user_phone,
            "properties_found": recommended_codes(conversation),
            "messages": [_serialize(message) for message in conversation.messages.all()],
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _serialize(message: Message) -> dict[str, str]:
    return {
        "role": message.role,
        "content": message.content,
        "timestamp": _isoformat(message.timestamp),
    }


def _isoformat(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
