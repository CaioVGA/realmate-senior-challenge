from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from assistant.runner import AssistantReply
from conversations.models import Conversation, Message, MessageRole, Recommendation
from conversations.tasks import process_conversation
from properties.models import Property

pytestmark = pytest.mark.django_db


def add_customer_message(conversation: Conversation, external_id: str, content: str) -> Message:
    return Message.objects.create(
        conversation=conversation,
        external_id=external_id,
        role=MessageRole.CUSTOMER,
        content=content,
        timestamp=datetime(2026, 6, 2, 10, 0, tzinfo=UTC),
    )


def test_debounce_descarta_execucao_de_mensagem_superada(
    conversation: Conversation, mocker: MockerFixture
) -> None:
    generate_reply = mocker.patch("conversations.tasks.generate_reply")
    first = add_customer_message(conversation, "m1", "Oi")
    add_customer_message(conversation, "m2", "bom dia")

    process_conversation(conversation.pk, first.pk)

    generate_reply.assert_not_called()


def test_ultima_mensagem_da_rajada_gera_um_unico_processamento(
    conversation: Conversation, properties: list[Property], mocker: MockerFixture
) -> None:
    generate_reply = mocker.patch(
        "conversations.tasks.generate_reply",
        return_value=AssistantReply(content="Encontrei 2 opções", recommended_codes=("IMV-002", "IMV-001")),
    )
    add_customer_message(conversation, "m1", "Oi")
    last = add_customer_message(conversation, "m2", "quero alugar em Boa Viagem até 3000")

    process_conversation(conversation.pk, last.pk)

    turns = generate_reply.call_args.args[0]
    assert [turn.content for turn in turns] == ["Oi", "quero alugar em Boa Viagem até 3000"]
    assert conversation.messages.filter(role=MessageRole.ASSISTANT).count() == 1
    assert list(Recommendation.objects.values_list("property__code", flat=True)) == ["IMV-002", "IMV-001"]


def test_imoveis_ja_recomendados_sao_enviados_para_o_assistente(
    conversation: Conversation, properties: list[Property], mocker: MockerFixture
) -> None:
    Recommendation.objects.create(conversation=conversation, property=properties[0])
    generate_reply = mocker.patch(
        "conversations.tasks.generate_reply",
        return_value=AssistantReply(content="ok", recommended_codes=()),
    )
    last = add_customer_message(conversation, "m1", "quero mais opções")

    process_conversation(conversation.pk, last.pk)

    assert generate_reply.call_args.args[1] == ["IMV-001"]
