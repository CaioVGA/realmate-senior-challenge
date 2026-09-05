from typing import TypedDict

from django.conf import settings

from assistant.context import ToolContext
from assistant.tools.base import Tool, ToolArguments
from common import coercion
from properties.models import Property, TransactionType
from properties.services import IncompleteFiltersError, PropertyFilters, search_properties

MISSING_FILTER_LABELS = {
    "tipo_negocio": "se é para aluguel ou venda",
    "bairro": "o bairro desejado",
    "preco": "um valor máximo ou mínimo de preço",
}


class PropertyPayload(TypedDict):
    codigo: str
    tipo_negocio: str
    bairro: str
    preco: float
    quartos: int
    endereco: str
    descricao: str


class SearchSuccess(TypedDict):
    total: int
    imoveis: list[PropertyPayload]


class MissingFilters(TypedDict):
    erro: str
    campos_faltando: list[str]
    mensagem: str


def find_properties(context: ToolContext, arguments: ToolArguments) -> SearchSuccess | MissingFilters:
    filters = PropertyFilters(
        code=coercion.as_text(arguments.get("codigo")),
        transaction_type=(coercion.as_text(arguments.get("tipo_negocio")) or "").lower() or None,
        neighborhood=coercion.as_text(arguments.get("bairro")),
        min_price=coercion.as_decimal(arguments.get("preco_minimo")),
        max_price=coercion.as_decimal(arguments.get("preco_maximo")),
        bedrooms=coercion.as_int(arguments.get("quartos")),
    )

    try:
        found = search_properties(
            filters,
            exclude_codes=sorted(context.excluded_codes),
            limit=settings.MAX_PROPERTIES_PER_SEARCH,
        )
    except IncompleteFiltersError as error:
        return MissingFilters(
            erro="filtros_insuficientes",
            campos_faltando=list(error.missing),
            mensagem="Pergunte ao cliente: " + "; ".join(MISSING_FILTER_LABELS[field] for field in error.missing),
        )

    for listing in found:
        context.register_recommendation(listing.code)
    return SearchSuccess(total=len(found), imoveis=[_serialize(listing) for listing in found])


def _serialize(listing: Property) -> PropertyPayload:
    return PropertyPayload(
        codigo=listing.code,
        tipo_negocio=listing.transaction_type,
        bairro=listing.neighborhood,
        preco=float(listing.price),
        quartos=listing.bedrooms,
        endereco=listing.address,
        descricao=listing.description,
    )


property_search_tool = Tool(
    name="buscar_imoveis",
    description=(
        "Busca imóveis residenciais em Recife/PE. Informe o código do imóvel OU, na falta dele, "
        "tipo de negócio, bairro e ao menos um limite de preço. Imóveis já apresentados nesta "
        "conversa são excluídos automaticamente."
    ),
    parameters={
        "type": "object",
        "properties": {
            "codigo": {
                "type": "string",
                "description": "Código do imóvel citado pelo cliente, por exemplo IMV-001 ou C011.",
            },
            "tipo_negocio": {
                "type": "string",
                "enum": list(TransactionType.values),
                "description": "Tipo de negócio desejado.",
            },
            "bairro": {"type": "string", "description": "Bairro desejado em Recife."},
            "preco_minimo": {"type": "number", "description": "Piso de preço em reais."},
            "preco_maximo": {"type": "number", "description": "Teto de preço em reais."},
            "quartos": {"type": "integer", "description": "Quantidade exata de quartos (opcional)."},
        },
        "additionalProperties": False,
    },
    handler=find_properties,
)
