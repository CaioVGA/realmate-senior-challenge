from collections.abc import Callable
from contextlib import AbstractContextManager

import pytest
from django.http import HttpResponse
from django.test import Client
from pytest_mock import MockerFixture

from conversations.models import Conversation, Message

pytestmark = pytest.mark.django_db

MESSAGE_ID = "3287ac71-8b6b-4deb-a497-5b902676f097"
PHONE = "+5581982860171"

CaptureOnCommit = Callable[..., AbstractContextManager[list[Callable[[], object]]]]


def message_event(**overrides: str) -> dict[str, object]:
    content: dict[str, str] = {
        "message_id": MESSAGE_ID,
        "user_phone_number": PHONE,
        "message_content": "Olá, procuro um apartamento",
        "timestamp": "2026-06-02T10:00:00Z",
    }
    content.update(overrides)
    return {"event": "MESSAGE_RECEIVED", "content": content}


def post(client: Client, payload: dict[str, object]) -> HttpResponse:
    return client.post("/webhook/message", data=payload, content_type="application/json")


def test_mensagem_recebida_e_persistida_e_enfileirada(
    client: Client,
    mocker: MockerFixture,
    django_capture_on_commit_callbacks: CaptureOnCommit,
) -> None:
    schedule = mocker.patch("conversations.services.ingestion.schedule_conversation_processing")

    with django_capture_on_commit_callbacks(execute=True):
        response = post(client, message_event())

    assert response.status_code == 200
    assert response.json() == {"status": "accepted", "message_id": MESSAGE_ID}
    message = Message.objects.get(external_id=MESSAGE_ID)
    assert message.role == "customer"
    assert message.conversation.user_phone == PHONE
    schedule.assert_called_once_with(message.conversation.pk, message.pk)


def test_evento_nao_suportado_e_ignorado(client: Client) -> None:
    payload: dict[str, object] = {
        "event": "MESSAGE_READ",
        "content": {"message_id": MESSAGE_ID, "read_at": "2026-06-02T10:00:10Z"},
    }

    response = post(client, payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "message_id": MESSAGE_ID}
    assert not Message.objects.exists()


def test_mensagem_duplicada_e_ignorada_silenciosamente(client: Client, mocker: MockerFixture) -> None:
    mocker.patch("conversations.services.ingestion.schedule_conversation_processing")
    post(client, message_event())

    response = post(client, message_event(message_content="reenvio"))

    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "message_id": MESSAGE_ID}
    assert Message.objects.count() == 1


def test_mensagens_do_mesmo_telefone_compartilham_a_conversa(client: Client, mocker: MockerFixture) -> None:
    mocker.patch("conversations.services.ingestion.schedule_conversation_processing")

    post(client, message_event())
    post(client, message_event(message_id="outro-id", message_content="bom dia"))

    assert Conversation.objects.count() == 1
    assert Message.objects.count() == 2


def test_payload_incompleto_retorna_400(client: Client) -> None:
    response = post(client, {"event": "MESSAGE_RECEIVED", "content": {"message_id": MESSAGE_ID}})

    assert response.status_code == 400
    assert not Message.objects.exists()
