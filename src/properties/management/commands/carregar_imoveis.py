from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from properties.services import import_properties
from properties.sources import SOURCES, build_sources


class Command(BaseCommand):
    help = "Carrega imóveis das origens configuradas (idempotente pelo código do imóvel)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--source",
            action="append",
            dest="sources",
            choices=sorted(SOURCES),
            help="Restringe a carga a uma origem. Pode ser repetido.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        selected: list[str] | None = options.get("sources")
        summary = import_properties(build_sources(selected))
        self.stdout.write(
            self.style.SUCCESS(
                f"Imóveis criados: {summary.created} | atualizados: {summary.updated} | ignorados: {summary.skipped}"
            )
        )
