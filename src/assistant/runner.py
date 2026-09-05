import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from django.conf import settings
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionFunctionToolParam,
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallUnion,
    ChatCompletionToolMessageParam,
)

from assistant.client import get_client
from assistant.context import ToolContext
from assistant.prompts import SYSTEM_PROMPT
from assistant.tools import AVAILABLE_TOOLS, ToolResult

logger = logging.getLogger(__name__)

FALLBACK_REPLY = "Desculpe, não consegui processar sua mensagem agora. Pode repetir, por favor?"


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class AssistantReply:
    content: str
    recommended_codes: tuple[str, ...]


def generate_reply(
    turns: Sequence[ConversationTurn],
    excluded_codes: Sequence[str] = (),
) -> AssistantReply:
    """Executa o ciclo de tool calling da OpenAI até obter a resposta final ao cliente."""
    context = ToolContext(excluded_codes={code.upper() for code in excluded_codes})
    messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_turn_param(turn) for turn in turns)

    for _ in range(settings.OPENAI_MAX_TOOL_ITERATIONS):
        completion = get_client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=_tool_params(),
        )
        message = completion.choices[0].message
        if not message.tool_calls:
            return _reply(message.content, context)

        messages.append(_assistant_param(message))
        messages.extend(_run_tool(context, tool_call) for tool_call in message.tool_calls)

    logger.warning("Limite de iterações de tools atingido sem resposta final")
    return _reply(None, context)


def _reply(content: str | None, context: ToolContext) -> AssistantReply:
    return AssistantReply(
        content=content or FALLBACK_REPLY,
        recommended_codes=tuple(context.recommended_codes),
    )


def _tool_params() -> list[ChatCompletionFunctionToolParam]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in AVAILABLE_TOOLS.values()
    ]


def _turn_param(turn: ConversationTurn) -> ChatCompletionMessageParam:
    if turn.role == "assistant":
        assistant: ChatCompletionAssistantMessageParam = {"role": "assistant", "content": turn.content}
        return assistant
    return {"role": "user", "content": turn.content}


def _assistant_param(message: ChatCompletionMessage) -> ChatCompletionAssistantMessageParam:
    param: ChatCompletionAssistantMessageParam = {"role": "assistant", "content": message.content}
    param["tool_calls"] = [
        {
            "id": tool_call.id,
            "type": "function",
            "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
        }
        for tool_call in message.tool_calls or ()
        if isinstance(tool_call, ChatCompletionMessageFunctionToolCall)
    ]
    return param


def _run_tool(
    context: ToolContext,
    tool_call: ChatCompletionMessageToolCallUnion,
) -> ChatCompletionToolMessageParam:
    result = _execute(context, tool_call)
    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps(result, ensure_ascii=False),
    }


def _execute(context: ToolContext, tool_call: ChatCompletionMessageToolCallUnion) -> ToolResult:
    if not isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
        return {"erro": "tipo_de_tool_nao_suportado"}

    tool = AVAILABLE_TOOLS.get(tool_call.function.name)
    if tool is None:
        logger.warning("Tool desconhecida solicitada pelo modelo: %s", tool_call.function.name)
        return {"erro": "tool_desconhecida"}

    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        return {"erro": "argumentos_invalidos"}
    if not isinstance(arguments, dict):
        return {"erro": "argumentos_invalidos"}

    return tool.handler(context, arguments)
