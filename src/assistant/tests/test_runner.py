import json
from dataclasses import dataclass, field

import pytest
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageParam,
)
from openai.types.chat.chat_completion_message_function_tool_call import Function
from pytest_mock import MockerFixture

from assistant.runner import ConversationTurn, generate_reply
from properties.models import Property


@dataclass(frozen=True)
class FakeChoice:
    message: ChatCompletionMessage


@dataclass(frozen=True)
class FakeCompletion:
    choices: list[FakeChoice]


@dataclass
class FakeCompletions:
    """Duplo do `client.chat.completions` que devolve respostas pré-definidas e guarda o que recebeu."""

    replies: list[ChatCompletionMessage]
    sent: list[list[ChatCompletionMessageParam]] = field(default_factory=list)

    def create(
        self,
        *,
        model: str,
        messages: list[ChatCompletionMessageParam],
        tools: object,
    ) -> FakeCompletion:
        self.sent.append(list(messages))
        return FakeCompletion(choices=[FakeChoice(message=self.replies.pop(0))])


class FakeClient:
    def __init__(self, replies: list[ChatCompletionMessage]) -> None:
        self.completions = FakeCompletions(replies=replies)
        self.chat = self

    @property
    def sent(self) -> list[list[ChatCompletionMessageParam]]:
        return self.completions.sent


def tool_call_message(name: str, arguments: dict[str, object]) -> ChatCompletionMessage:
    return ChatCompletionMessage(
        role="assistant",
        content=None,
        tool_calls=[
            ChatCompletionMessageFunctionToolCall(
                id="call_1",
                type="function",
                function=Function(name=name, arguments=json.dumps(arguments)),
            )
        ],
    )


@pytest.mark.django_db
def test_ciclo_de_tool_calling_retorna_resposta_e_imoveis_recomendados(
    properties: list[Property], mocker: MockerFixture
) -> None:
    client = FakeClient(
        [
            tool_call_message(
                "buscar_imoveis",
                {"tipo_negocio": "aluguel", "bairro": "Boa Viagem", "preco_maximo": 3000},
            ),
            ChatCompletionMessage(role="assistant", content="Encontrei 2 opções para você."),
        ]
    )
    mocker.patch("assistant.runner.get_client", return_value=client)

    reply = generate_reply([ConversationTurn(role="user", content="quero alugar em Boa Viagem até 3 mil")])

    assert reply.content == "Encontrei 2 opções para você."
    assert reply.recommended_codes == ("IMV-001", "IMV-002")
    assert [message["role"] for message in client.sent[-1]] == ["system", "user", "assistant", "tool"]


@pytest.mark.django_db
def test_recomendacoes_anteriores_sao_excluidas_da_busca(
    properties: list[Property], mocker: MockerFixture
) -> None:
    client = FakeClient(
        [
            tool_call_message(
                "buscar_imoveis",
                {"tipo_negocio": "aluguel", "bairro": "Boa Viagem", "preco_maximo": 10000},
            ),
            ChatCompletionMessage(role="assistant", content="Mais uma opção."),
        ]
    )
    mocker.patch("assistant.runner.get_client", return_value=client)

    reply = generate_reply([ConversationTurn(role="user", content="mais opções")], excluded_codes=["IMV-001"])

    assert reply.recommended_codes == ("IMV-002", "IMV-003")


def test_tool_desconhecida_nao_interrompe_a_conversa(mocker: MockerFixture) -> None:
    client = FakeClient(
        [
            tool_call_message("tool_inexistente", {}),
            ChatCompletionMessage(role="assistant", content="Como posso ajudar?"),
        ]
    )
    mocker.patch("assistant.runner.get_client", return_value=client)

    reply = generate_reply([ConversationTurn(role="user", content="oi")])

    assert reply.content == "Como posso ajudar?"
    last = client.sent[-1][-1]
    assert last["role"] == "tool"
    assert json.loads(str(last["content"])) == {"erro": "tool_desconhecida"}
