import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

from common import coercion

logger = logging.getLogger(__name__)


class InvalidPropertyRow(ValueError):
    """Linha da fonte que não pode virar um imóvel válido."""


@dataclass(frozen=True, slots=True)
class PropertyRecord:
    code: str
    transaction_type: str
    neighborhood: str
    price: Decimal
    bedrooms: int
    address: str
    description: str


class PropertySource(ABC):
    """Contrato que qualquer origem de imóveis (arquivo, API, XML) precisa cumprir."""

    name: ClassVar[str]

    @abstractmethod
    def fetch(self) -> Iterator[PropertyRecord]:
        """Produz registros normalizados, um por imóvel disponível na origem."""


class FilePropertySource(PropertySource):
    """Base para origens em arquivo: cada formato só descreve como lê linhas e onde está o código."""

    code_pattern: ClassVar[re.Pattern[str]]

    def __init__(self, path: Path) -> None:
        self.path = path

    def fetch(self) -> Iterator[PropertyRecord]:
        for row in self.read_rows():
            try:
                yield self.build_record(row)
            except InvalidPropertyRow as error:
                logger.warning("Registro ignorado em %s: %s", self.path.name, error)

    @abstractmethod
    def read_rows(self) -> Iterator[Mapping[str, object]]:
        """Lê a origem e devolve linhas cruas com as chaves do formato original."""

    def build_record(self, row: Mapping[str, object]) -> PropertyRecord:
        description = _as_text(row.get("descricao"))
        return PropertyRecord(
            code=self.extract_code(description),
            transaction_type=_as_text(row.get("tipo_negocio")).lower(),
            neighborhood=_as_text(row.get("bairro")),
            price=_as_decimal(row.get("preco")),
            bedrooms=_as_int(row.get("quartos")),
            address=_as_text(row.get("endereco")),
            description=description,
        )

    def extract_code(self, description: str) -> str:
        match = self.code_pattern.search(description)
        if match is None:
            raise InvalidPropertyRow(f"código não encontrado na descrição: {description[:60]!r}")
        return match.group("code").upper()


def _as_text(value: object) -> str:
    return coercion.as_text(value) or ""


def _as_int(value: object) -> int:
    parsed = coercion.as_int(value)
    if parsed is None:
        raise InvalidPropertyRow(f"quantidade de quartos inválida: {value!r}")
    return parsed


def _as_decimal(value: object) -> Decimal:
    parsed = coercion.as_decimal(value)
    if parsed is None:
        raise InvalidPropertyRow(f"preço inválido: {value!r}")
    return parsed
