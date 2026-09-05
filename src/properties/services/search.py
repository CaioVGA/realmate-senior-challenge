from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db.models import QuerySet

from common.text import normalize
from properties.models import Property, TransactionType

REQUIRED_WITHOUT_CODE = ("tipo_negocio", "bairro", "preco")


class IncompleteFiltersError(ValueError):
    """Filtros insuficientes para uma busca: nenhum imóvel pode ser retornado."""

    def __init__(self, missing: Sequence[str]) -> None:
        self.missing = tuple(missing)
        super().__init__(f"filtros obrigatórios ausentes: {', '.join(self.missing)}")


@dataclass(frozen=True, slots=True)
class PropertyFilters:
    code: str | None = None
    transaction_type: str | None = None
    neighborhood: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    bedrooms: int | None = None

    def missing_required(self) -> tuple[str, ...]:
        if self.code:
            return ()
        missing = []
        if self.transaction_type not in TransactionType.values:
            missing.append("tipo_negocio")
        if not self.neighborhood:
            missing.append("bairro")
        if self.min_price is None and self.max_price is None:
            missing.append("preco")
        return tuple(missing)


def search_properties(
    filters: PropertyFilters,
    exclude_codes: Sequence[str] = (),
    limit: int | None = None,
) -> list[Property]:
    """Busca imóveis já garantindo os filtros mínimos: a checagem não depende do modelo de IA."""
    missing = filters.missing_required()
    if missing:
        raise IncompleteFiltersError(missing)

    queryset = _apply_filters(Property.objects.all(), filters)
    # Consulta por código é o cliente perguntando sobre um imóvel específico, não um pedido de novas
    # opções: aí a exclusão não se aplica, senão o assistente nega um imóvel que ele mesmo apresentou.
    if exclude_codes and not filters.code:
        queryset = queryset.exclude(code__in=[code.upper() for code in exclude_codes])
    return list(queryset[: limit or settings.MAX_PROPERTIES_PER_SEARCH])


def _apply_filters(queryset: QuerySet[Property], filters: PropertyFilters) -> QuerySet[Property]:
    if filters.code:
        return queryset.filter(code__iexact=filters.code)

    queryset = queryset.filter(
        transaction_type=filters.transaction_type,
        neighborhood_key=normalize(filters.neighborhood or ""),
    )
    if filters.min_price is not None:
        queryset = queryset.filter(price__gte=filters.min_price)
    if filters.max_price is not None:
        queryset = queryset.filter(price__lte=filters.max_price)
    if filters.bedrooms is not None:
        queryset = queryset.filter(bedrooms=filters.bedrooms)
    return queryset
