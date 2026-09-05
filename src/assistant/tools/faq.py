import json
from functools import lru_cache
from typing import NotRequired, TypedDict

from django.conf import settings

from assistant.context import ToolContext
from assistant.tools.base import Tool, ToolArguments
from common import coercion
from common.text import tokenize

MAX_RESULTS = 3


class FaqEntry(TypedDict):
    pergunta: str
    resposta: str


class FaqResult(TypedDict):
    resultados: list[FaqEntry]
    mensagem: NotRequired[str]


@lru_cache(maxsize=1)
def _entries() -> tuple[FaqEntry, ...]:
    raw: list[dict[str, str]] = json.loads(
        (settings.DATA_DIR / "perguntas_frequentes.json").read_text(encoding="utf-8")
    )
    return tuple(FaqEntry(pergunta=item["pergunta"], resposta=item["resposta"]) for item in raw)


def _keywords(entry: FaqEntry) -> set[str]:
    return tokenize(entry["pergunta"] + " " + entry["resposta"])


def search_faq(context: ToolContext, arguments: ToolArguments) -> FaqResult:
    question = coercion.as_text(arguments.get("pergunta"))
    if question is None:
        return {"resultados": [], "mensagem": "Informe a dúvida do cliente para consultar a base."}

    wanted = tokenize(question)
    scored = [(len(wanted & _keywords(entry)), entry) for entry in _entries()]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = [entry for score, entry in scored[:MAX_RESULTS] if score > 0]
    if not results:
        return {"resultados": [], "mensagem": "Nenhuma informação sobre esse assunto na base da imobiliária."}
    return {"resultados": results}


faq_tool = Tool(
    name="consultar_faq",
    description=(
        "Consulta a base de perguntas frequentes da imobiliária (documentos, taxas, garantias, "
        "visitas, contrato, pagamento, pets). Use sempre que o cliente perguntar sobre regras da "
        "imobiliária e responda apenas com o conteúdo retornado."
    ),
    parameters={
        "type": "object",
        "properties": {
            "pergunta": {
                "type": "string",
                "description": "Dúvida do cliente, com as palavras-chave do assunto.",
            }
        },
        "required": ["pergunta"],
        "additionalProperties": False,
    },
    handler=search_faq,
)
