from datetime import UTC, datetime, timedelta

import pytest
from django.test import Client
from django.utils import timezone

from conversations.models import Conversation, Message, MessageRole, Recommendation
from conversations.services.replies import store_assistant_reply
from properties.models import Property

pytestmark = pytest.mark.django_db


def test_historico_segue_o_contrato_e_a_ordem_cronologica(
    client: Client, conversation: Conversation, properties: list[Property]
) -> None:
    Message.objects.create(
        conversation=conversation,
        external_id="m2",
        role=MessageRole.ASSISTANT,
        content="Encontrei 2 imóveis",
        timestamp=datetime(2026, 6, 2, 10, 0, 5, tzinfo=UTC),
    )
    Message.objects.create(
        conversation=conversation,
        external_id="m1",
        role=MessageRole.CUSTOMER,
        content="Olá",
        timestamp=datetime(2026, 6, 2, 10, 0, 0, tzinfo=UTC),
    )
    Recommendation.objects.create(conversation=conversation, property=properties[0])

    response = client.get(f"/api/conversations/{conversation.user_phone}/messages")

    assert response.status_code == 200
    assert response.json() == {
        "user_phone": "+5581982860171",
        "properties_found": ["IMV-001"],
        "messages": [
            {"role": "customer", "content": "Olá", "timestamp": "2026-06-02T10:00:00Z"},
            {"role": "assistant", "content": "Encontrei 2 imóveis", "timestamp": "2026-06-02T10:00:05Z"},
        ],
    }


def test_conversa_inexistente_retorna_404(client: Client) -> None:
    response = client.get("/api/conversations/+5581999999999/messages")

    assert response.status_code == 404


def test_resposta_nunca_fica_antes_da_mensagem_do_cliente(conversation: Conversation) -> None:
    futuro = timezone.now() + timedelta(days=30)
    Message.objects.create(
        conversation=conversation,
        external_id="m1",
        role=MessageRole.CUSTOMER,
        content="mensagem com timestamp adiantado",
        timestamp=futuro,
    )
    conversation.register_activity(futuro)

    reply = store_assistant_reply(conversation, "resposta")

    assert reply.timestamp > futuro
    assert [message.content for message in conversation.messages.all()] == [
        "mensagem com timestamp adiantado",
        "resposta",
    ]
