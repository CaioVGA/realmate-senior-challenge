import logging
from collections.abc import Sequence
from dataclasses import dataclass

from django.db import transaction

from properties.models import Property, TransactionType
from properties.sources import PropertyRecord, PropertySource, build_sources

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ImportSummary:
    created: int = 0
    updated: int = 0
    skipped: int = 0

    def __add__(self, other: "ImportSummary") -> "ImportSummary":
        return ImportSummary(
            created=self.created + other.created,
            updated=self.updated + other.updated,
            skipped=self.skipped + other.skipped,
        )


def import_properties(sources: Sequence[PropertySource] | None = None) -> ImportSummary:
    """Carrega imóveis de todas as origens informadas usando o código como chave de unicidade."""
    summary = ImportSummary()
    for source in sources if sources is not None else build_sources():
        source_summary = _import_source(source)
        logger.info("Carga da origem %s: %s", source.name, source_summary)
        summary += source_summary
    return summary


def _import_source(source: PropertySource) -> ImportSummary:
    summary = ImportSummary()
    for record in source.fetch():
        if record.transaction_type not in TransactionType.values:
            logger.warning("Imóvel %s ignorado: tipo de negócio %r", record.code, record.transaction_type)
            summary += ImportSummary(skipped=1)
            continue
        with transaction.atomic():
            _, created = Property.objects.update_or_create(
                code=record.code,
                defaults=_defaults(record, source.name),
            )
        summary += ImportSummary(created=1) if created else ImportSummary(updated=1)
    return summary


def _defaults(record: PropertyRecord, source_name: str) -> dict[str, object]:
    return {
        "transaction_type": record.transaction_type,
        "neighborhood": record.neighborhood,
        "price": record.price,
        "bedrooms": record.bedrooms,
        "address": record.address,
        "description": record.description,
        "source": source_name,
    }
